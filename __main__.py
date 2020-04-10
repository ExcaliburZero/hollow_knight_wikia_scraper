from dataclasses import dataclass
from typing import List, IO, Set, Optional

import abc
import argparse
import os
import sys
import urllib.parse

import bs4
import wikia


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("start_page")
    parser.add_argument("--max_num_pages", type=int, default=None)
    parser.add_argument("--page_html_dir", default="page_html")

    args = parser.parse_args(argv)

    print(args)

    config = Config.from_args(args)
    io_manager = IOManager.default_streams(config)

    if not config.validate(io_manager):
        print("Invalid flags")
        sys.exit(1)

    run(config, io_manager)


@dataclass
class Config:
    wiki_name: str
    start_page: str
    page_html_dir: str
    max_num_pages: Optional[int]

    def validate(self, io_manager: "IOManager") -> bool:
        success = True

        if self.max_num_pages is not None and self.max_num_pages <= 0:
            success = False
            io_manager.error_stream.write(
                '"max_num_pages" cannot be {}, it must be a positive integer\n'.format(
                    self.max_num_pages
                )
            )

        return success

    def should_download_more_pages(self, num_pages_downloaded: int) -> bool:
        return self.max_num_pages is None or num_pages_downloaded < self.max_num_pages

    @staticmethod
    def from_args(args: argparse.Namespace) -> "Config":
        return Config(
            wiki_name="HollowKnight",
            start_page=args.start_page,
            page_html_dir=args.page_html_dir,
            max_num_pages=args.max_num_pages,
        )


class PageWriter(abc.ABC):
    @abc.abstractmethod
    def write_html(self, page_name: str, html: str) -> str:
        raise NotImplementedError


@dataclass
class FilesystemPageWriter(PageWriter):
    html_dir: str

    def write_html(self, page_name: str, html: str) -> str:
        filepath = os.path.join(self.html_dir, "{}.html".format(page_name))

        os.makedirs(self.html_dir, exist_ok=True)

        with open(filepath, "w") as output_stream:
            output_stream.write(html)

        return filepath


@dataclass
class IOManager:
    output_stream: IO[str]
    error_stream: IO[str]
    html_writer: PageWriter

    @staticmethod
    def default_streams(config: Config) -> "IOManager":
        return IOManager(
            output_stream=sys.stdout,
            error_stream=sys.stderr,
            html_writer=FilesystemPageWriter(config.page_html_dir),
        )


@dataclass
class Page:
    name: str
    outgoing_links: Set[str]
    html_path: str


def run(config: Config, io_manager: "IOManager") -> None:
    assert config.validate(io_manager)

    pages = recursively_download_pages(config, io_manager, config.start_page)

    for page in pages:
        print(page)


def recursively_download_pages(
    config: Config, io_manager: "IOManager", start_page: str
) -> List[Page]:
    pages_to_download = {start_page}
    downloaded_page_names: Set[str] = set()
    downloaded_pages: List[Page] = []

    while True:
        # Stop if we run out of pages to download
        if len(pages_to_download) == 0:
            break

        # Stop if we hit the page download limit
        if not config.should_download_more_pages(len(downloaded_pages)):
            assert config.max_num_pages is not None
            io_manager.output_stream.write(
                "Reached limit of max number of pages to download ({})\n".format(
                    config.max_num_pages
                )
            )

            break

        page_name = pages_to_download.pop()

        page = download_page(config, io_manager, page_name)

        downloaded_pages.append(page)
        downloaded_page_names.add(page_name)

        for outgoing_link in page.outgoing_links:
            if outgoing_link not in downloaded_page_names:
                pages_to_download.add(outgoing_link)

    return downloaded_pages


def download_page(config: Config, io_manager: IOManager, page_name: str) -> Page:
    page = wikia.page(config.wiki_name, page_name)
    html = page.html()
    soup = bs4.BeautifulSoup(html, "html.parser")

    outgoing_links = parse_outgoing_links(soup)

    html_path = io_manager.html_writer.write_html(page_name, html)

    return Page(name=page_name, html_path=html_path, outgoing_links=outgoing_links,)


def parse_outgoing_links(soup: bs4.BeautifulSoup) -> Set[str]:
    links = (a.get("href") for a in soup.find(id="WikiaArticle").find_all("a"))

    wiki_links = (
        link[len("/wiki/") :]
        for link in links
        if link is not None and link.startswith("/wiki/")
    )

    return {
        urllib.parse.unquote(remove_link_subsection(link))
        for link in wiki_links
        if (not link.startswith("Category:")) and (not link.startswith("File:"))
    }


def remove_link_subsection(link: str) -> str:
    return link.split("#")[0]


if __name__ == "__main__":
    main(sys.argv[1:])
