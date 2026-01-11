#!/usr/bin/env python3

import argparse
from pathlib import Path
import re
from zipfile import ZipFile

__COPYRIGHT__ = "Copyright © by XA, I 2026. All rights reserved."
__VERSION__ = "1.1.0"


class patch_xml_projectversion:
    """
    Patch ‹version› into ‹set_ver› in `<ProjectVersion>‹version›</ProjectVersion>` sequence of data_bytes (UTF-8).

    This should not technically be necessary, as the relevant project version is stored in an XML tag.
    """

    re_projectversion = re.compile(r"<ProjectVersion>\s*(\d+)\s*</ProjectVersion>")

    def __new__(cls, data_bytes: bytes, *, set_ver: str, assert_ver: str = "") -> bytes:
        """
        Construction with `__new__` makes class directly callable (w/o instantiation) and the re compiled only once.

        :param data_bytes: input data bytes
        :param set_ver: version string to set
        :param assert_ver: if not empty, assert that existing version matches this string
        :return: modified data bytes
        """
        data = data_bytes.decode()
        m = cls.re_projectversion.search(data)
        if m is not None:
            if assert_ver != "" and m.group(1) != str(assert_ver):
                raise AssertionError({"ver": str(m.group(1))})
            else:
                data = data[: m.start(1)] + str(set_ver) + data[m.end(1) :]
                data_bytes = data.encode()
        return data_bytes


class patch_comment_version_info:
    """
    Patch ‹version› tags of DR and project version info in XML comment in any xml file of the project.
    """

    re = re.compile(r"""<!--\s*DbAppVer="(?P<appver>[\d.]+)"\s+DbPrjVer="(?P<projver>[\d.]+)"\s*-->""")

    def __new__(cls, data_bytes: bytes, *, set_ver: str, assert_ver: str = "", set_appver: str = "") -> bytes:
        """
        Construction with `__new__` makes class directly callable (w/o instantiation) and the re compiled only once.

        :param data_bytes: input data bytes
        :param set_ver: version string to set
        :param assert_ver: if not empty, assert that existing version matches this string
        :return: modified data bytes
        """
        data = data_bytes.decode()
        m = cls.re.search(data)
        if m is not None:
            if assert_ver != "" and m.group("projver") is not None and m.group("projver") != str(assert_ver):
                raise AssertionError({"ver": str(m.group("projver"))})
            else:
                data = data[: m.start("projver")] + str(set_ver) + data[m.end("projver") :]
                if set_appver != "":
                    data = data[: m.start("appver")] + str(set_appver) + data[m.end("appver") :]
                data_bytes = data.encode()
        return data_bytes


def process_dr_project(
    inputfile: Path | str, outputfile: Path | str, *, set_ver: str, assert_ver: str = "", set_appver: str = ""
) -> None:
    """
    Process Davinci Resolve® project file (.drp) to set project version.

    :param inputfile: input project file path
    :param outputfile: output project file path
    :param set_ver: version string to set
    :param set_appver: application version string to set in comment info
    :param assert_ver: if not empty, assert that existing version matches this string
    """

    with ZipFile(inputfile, "r") as in_project:
        infolist = in_project.infolist()

        with ZipFile(outputfile, "w") as out_project:

            for in_item_name in infolist:
                with in_project.open(in_item_name) as in_item:
                    data_bytes = in_item.read()

                    if in_item_name.filename.endswith("roject.xml"):
                        # patch version data
                        try:
                            data_bytes = patch_xml_projectversion(data_bytes, set_ver=set_ver, assert_ver=assert_ver)
                        except AssertionError as e:
                            print(
                                f"Project version {e.args[0]["ver"]} in file is not expected version {assert_ver}. Skipping modification."
                            )
                            pass
                    if set_appver != "" and in_item_name.filename.endswith(".xml"):
                        # patch comment version info
                        try:
                            data_bytes = patch_comment_version_info(
                                data_bytes, set_ver=set_ver, assert_ver=assert_ver, set_appver=set_appver
                            )
                        except AssertionError as e:
                            print(
                                f"Project version {e.args[0]['ver']} in file is not expected version {assert_ver}. Skipping modification."
                            )
                            pass

                    # copy item over
                    out_project.writestr(in_item_name, data_bytes)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description=f"Set a version for Davinci Resolve® project files.",
        epilog=f"Version {__VERSION__}. {__COPYRIGHT__}",
        suggest_on_error=True,
    )

    parser.add_argument(
        "-s", "--setver", type=str, required=True, help="project version string to write into project file"
    )
    parser.add_argument(
        "-a", "--assertver", type=str, default="", help="assert that existing project file bears given version"
    )
    parser.add_argument(
        "-A", "--appver", type=str, default="", help="DR application version string to write into project file comments"
    )
    parser.add_argument("input", type=Path, help="input project file (.drp)")
    parser.add_argument("output", type=Path, help="modified output project file (.drp)")

    return parser.parse_args()


def main():
    """Main function."""
    args: argparse.Namespace = parse_arguments()

    process_dr_project(args.input, args.output, set_ver=args.setver, assert_ver=args.assertver, set_appver=args.appver)


if __name__ == "__main__":
    main()
