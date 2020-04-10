from dataclasses import dataclass
from typing import List, IO, Set, Optional

import argparse
import sys

import bs4
import wikia


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("start_page")
    parser.add_argument("--max_num_pages", type=int, default=None)

    args = parser.parse_args(argv)

    print(args)

    config = Config.from_args(args)

    if not config.validate():
        print("Invalid flags")
        sys.exit(1)

    run(config)


@dataclass
class Config:
    wiki_name: str
    start_page: str
    max_num_pages: Optional[int]

    def validate(self, error_stream: IO[str] = sys.stderr) -> bool:
        success = True

        if self.max_num_pages is not None and self.max_num_pages <= 0:
            success = False
            error_stream.write(
                '"max_num_pages" cannot be {}, it must be a positive integer'.format(
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
            max_num_pages=args.max_num_pages,
        )


@dataclass
class Page:
    name: str
    outgoing_links: Set[str]
    html: str


def run(config: Config) -> None:
    assert config.validate()

    pages = recursively_download_pages(config, config.start_page)

    for page in pages:
        print(page)


def recursively_download_pages(config: Config, start_page: str) -> List[Page]:
    pages_to_download = {start_page}
    downloaded_page_names: Set[str] = set()
    downloaded_pages: List[Page] = []

    while len(pages_to_download) > 0 and config.should_download_more_pages(
        len(downloaded_pages)
    ):
        page_name = pages_to_download.pop()

        page = download_page(config, page_name)

        downloaded_pages.append(page)
        downloaded_page_names.add(page_name)

        for outgoing_link in page.outgoing_links:
            if outgoing_link not in downloaded_page_names:
                pages_to_download.add(outgoing_link)

    # TODO: maybe yield a message when we reach the max num downloads and want to download another

    return downloaded_pages


def download_page(config: Config, page_name: str) -> Page:
    page = wikia.page(config.wiki_name, page_name)
    html = page.html()
    soup = bs4.BeautifulSoup(html, "html.parser")

    outgoing_links = parse_outgoing_links(soup)

    return Page(
        name=page_name,
        # html = html,
        html="",
        outgoing_links=outgoing_links,
    )


def parse_outgoing_links(soup: bs4.BeautifulSoup) -> Set[str]:
    links = (a.get("href") for a in soup.find(id="WikiaArticle").find_all("a"))

    wiki_links = (link[len("/wiki/") :] for link in links if link.startswith("/wiki/"))

    return {
        remove_link_subsection(link)
        for link in wiki_links
        if (not link.startswith("Category:")) and (not link.startswith("File:"))
    }


def remove_link_subsection(link: str) -> str:
    return link.split("#")[0]


if __name__ == "__main__":
    main(sys.argv[1:])