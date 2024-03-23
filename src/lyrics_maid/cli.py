import argparse
import importlib.metadata
import logging
from pathlib import Path

from .log import logger
from .lyrics import fetch_lyrics

__version__ = importlib.metadata.version("lyrics-maid")


def comma_separated_list(txt: str):
    return txt.lower().split(",")


def load_agrparses():
    # TODO read default settings in config file
    parser = argparse.ArgumentParser(
        prog="lyrics-maid",
        description="Automatically fetch lyrics for your local music files",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s, version " + __version__,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="use `-v` for debug output",
        action="store_true",
        default=0,
    )
    subparsers = parser.add_subparsers(title="commands")

    fetch_parser = subparsers.add_parser(
        "fetch", help="fecth lyrics for all the media files in the provided directory"
    )
    fetch_parser.add_argument(
        "directory",
        type=Path,
        help="the directory that contains the media files",
    )
    fetch_parser.add_argument(
        "-s",
        "--skip",
        help="skip files that contains a keyword specifed in the list (e.g. instumental)",
        type=comma_separated_list,
        default=[],
    )
    fetch_parser.add_argument(
        "-f",
        "--force",
        help="overwrite existing lyrics if it alredy exists",
        action="store_true",
        default=False,
    )
    fetch_parser.set_defaults(func=fetch_lyrics)
    return parser


def cli_main():
    parser = load_agrparses()
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("Parsed args=%s" % args)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
