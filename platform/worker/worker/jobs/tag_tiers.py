"""Tag symbols large-cap vs mid/small from the NIFTY 100 list. Run once (and again
whenever the index reconstitutes, ~twice a year). The screen's universe pre-filter
excludes 'large' so swing trading focuses on the faster-moving mid/small caps."""

from worker.repo import record_job, tag_tiers
from worker.sources.nse import fetch_largecap_symbols


def main() -> None:
    largecaps = fetch_largecap_symbols()
    if not largecaps:
        print("could not fetch NIFTY 100 list — no tags written")
        record_job("tag_tiers", "failed", {"large": 0})
        return
    res = tag_tiers(largecaps)
    record_job("tag_tiers", "ok", res)
    print(f"tagged {res['large']} large-cap (NIFTY 100), "
          f"{res['total'] - res['large']} mid/small")


if __name__ == "__main__":
    main()
