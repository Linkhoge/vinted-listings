import json
import argparse
import re
from playwright.sync_api import sync_playwright

DEFAULT_PROFILE = "https://www.vinted.ie/member/3146447592"


def extract_profile_id(profile_url: str) -> str:
    match = re.search(r"/member/(\d+)", profile_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract profile id from URL: {profile_url}")


def scrape_listings(profile_url: str):
    profile_id = extract_profile_id(profile_url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(profile_url, timeout=60000)
        page.wait_for_load_state("networkidle")

        items = page.evaluate(
            """
        async (profileId) => {
            const listings = [];
            const perPage = 50;
            let pageIndex = 1;
            while (true) {
                const endpoint = `/api/v2/wardrobe/${profileId}/items?page=${pageIndex}&per_page=${perPage}&order=relevance`;
                const response = await fetch(endpoint, {
                    headers: {
                        'Accept': 'application/json, text/plain, */*',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    credentials: 'same-origin',
                });

                if (!response.ok) {
                    break;
                }

                const payload = await response.json();
                if (!payload?.items?.length) {
                    break;
                }

                for (const item of payload.items) {
                    const image = item.photo?.thumbnails?.find((thumb) => thumb.type === 'thumb310')?.url
                        || item.photo?.url
                        || null;
                    const url = item.path ? `https://www.vinted.ie${item.path}` : item.url || null;
                    listings.push({
                        'id': item.id,
                        'title': item.title,
                        'price': item.price?.amount || null,
                        'currency': item.price?.currency_code || item.currency || null,
                        'url': url,
                        'image': image,
                        'status': item.status || null,
                        'raw': item,
                    });
                }

                if (payload.items.length < perPage) {
                    break;
                }
                pageIndex += 1;
                if (pageIndex > 20) {
                    break;
                }
            }
            return listings;
        }
        """,
            profile_id,
        )

        browser.close()
        return items


def save_as_json(data, output_path: str):
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape Vinted listings for a public profile and save to JSON.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="Vinted profile URL to scrape")
    parser.add_argument("--output", default="vinted_listings.json", help="JSON output file path")
    return parser.parse_args()


def main():
    args = parse_args()
    print(f"Scraping profile: {args.profile}")
    listings = scrape_listings(args.profile)
    save_as_json(listings, args.output)
    print(f"Saved {len(listings)} listings to {args.output}")


if __name__ == "__main__":
    main()
