"""
Analyse a conference by calling the main function of the analyse conference package

Supported conferences:
- SIGIR2022
"""
import analyse_conf
import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("conference", type=str, help="name and year of the conference")
    args = parser.parse_args()

    supported_conferences = list(analyse_conf.CONFERENCE_TO_WEBSCRAPER.keys())
    if args.conference not in supported_conferences:
        raise ValueError(f"{args.conference=} is not one of the supported conferences: {supported_conferences}")
    analyse_conf.analyse_conf(args.conference)


if __name__ == "__main__":
    main()
