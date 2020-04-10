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

    @staticmethod
    def from_args(args: argparse.Namespace) -> "Config":
        return Config(
            wiki_name="HollowKnight",
            start_page=args.start_page,
            max_num_pages=args.max_num_pages,
        )


def run(config: Config) -> None:
    assert config.validate()

    start_page = download_page(config, config.start_page)

    print(start_page)


@dataclass
class Page:
    name: str
    outgoing_links: Set[str]
    html: str


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
