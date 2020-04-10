from dataclasses import dataclass
from typing import List, IO, Set, Optional

import abc
import argparse
import csv
import os
import sys
import urllib.parse

import bs4
import progressbar
import wikia


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("start_page")
    parser.add_argument("--max_num_pages", type=int, default=None)
    parser.add_argument("--pages_csv", default="pages.csv")
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
    pages_csv: str
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
            pages_csv=args.pages_csv,
            page_html_dir=args.page_html_dir,
            max_num_pages=args.max_num_pages,
        )


class FileWriter(abc.ABC):
    @abc.abstractmethod
    def write_html(self, page_name: str, html: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def write_pages_csv(self, pages: List["Page"]) -> str:
        raise NotImplementedError


@dataclass
class FilesystemWriter(FileWriter):
    pages_csv: str
    html_dir: str

    def write_html(self, page_name: str, html: str) -> str:
        filepath = os.path.join(self.html_dir, "{}.html".format(page_name))

        os.makedirs(self.html_dir, exist_ok=True)

        with open(filepath, "w") as output_stream:
            output_stream.write(html)

        return filepath

    def write_pages_csv(self, pages: List["Page"]) -> str:
        columns = ["page_name", "outgoing_links", "local_html_path"]

        with open(self.pages_csv, "w") as output_stream:
            writer = csv.DictWriter(output_stream, columns)

            writer.writeheader()
            for page in sorted(pages, key=lambda p: p.name):
                writer.writerow(
                    {
                        "page_name": page.name,
                        "outgoing_links": " ".join(page.outgoing_links),
                        "local_html_path": page.html_path,
                    }
                )

        return self.pages_csv


@dataclass
class IOManager:
    output_stream: IO[str]
    error_stream: IO[str]
    file_writer: FileWriter

    @staticmethod
    def default_streams(config: Config) -> "IOManager":
        return IOManager(
            output_stream=sys.stdout,
            error_stream=sys.stderr,
            file_writer=FilesystemWriter(
                pages_csv=config.pages_csv, html_dir=config.page_html_dir
            ),
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

    io_manager.file_writer.write_pages_csv(pages)


def recursively_download_pages(
    config: Config, io_manager: "IOManager", start_page: str
) -> List[Page]:
    pages_to_download = {start_page}
    downloaded_page_names: Set[str] = set()
    downloaded_pages: List[Page] = []

    pbar = progressbar.ProgressBar(fd=io_manager.output_stream)

    i = 0
    while True:
        # Stop if we run out of pages to download
        if len(pages_to_download) == 0:
            break

        # Stop if we hit the page download limit
        if not config.should_download_more_pages(len(downloaded_pages)):
            pbar.finish()

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

        # Account for cases where the page is redirected
        downloaded_page_names.add(page.name)
        pages_to_download.discard(page.name)

        # TODO: keep track of and resolve redirects

        for outgoing_link in page.outgoing_links:
            if outgoing_link not in downloaded_page_names:
                pages_to_download.add(outgoing_link)

        i += 1
        pbar.update(i)

    return downloaded_pages


def download_page(config: Config, io_manager: IOManager, page_name: str) -> Page:
    page = wikia.page(config.wiki_name, page_name)
    page_name_resolved = page.title.replace(" ", "_")

    html = page.html()
    soup = bs4.BeautifulSoup(html, "html.parser")

    outgoing_links = parse_outgoing_links(soup)

    html_path = io_manager.file_writer.write_html(page_name_resolved, html)

    return Page(
        name=page_name_resolved, html_path=html_path, outgoing_links=outgoing_links,
    )


def remove_lore_prefix(page_name: str) -> str:
    if page_name.startswith("Lore/"):
        return page_name[len("Lore/") :]
    else:
        return page_name


def parse_outgoing_links(soup: bs4.BeautifulSoup) -> Set[str]:
    links = (a.get("href") for a in soup.find(id="WikiaArticle").find_all("a"))

    wiki_links = (
        link[len("/wiki/") :]
        for link in links
        if link is not None and link.startswith("/wiki/")
    )

    return {
        urllib.parse.unquote(remove_lore_prefix(remove_link_subsection(link)))
        for link in wiki_links
        if ":" not in link
    }


def remove_link_subsection(link: str) -> str:
    return link.split("#")[0]


if __name__ == "__main__":
    main(sys.argv[1:])
