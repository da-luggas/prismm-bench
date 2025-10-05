import openreview
import pickle
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Download reviews from OpenReview")
    parser.add_argument("--username", default=os.getenv("OPENREVIEW_USERNAME"), help="OpenReview username")
    parser.add_argument("--password", default=os.getenv("OPENREVIEW_PASSWORD"), help="OpenReview password")
    parser.add_argument("--venue-id", default=os.getenv("VENUE_ID", "ICLR.cc/2025/Conference"), help="Venue ID")
    parser.add_argument("--output-file", default=os.getenv("OUTPUT_FILE", "iclr_2025_raw.pkl"), help="Output pickle file")
    
    args = parser.parse_args()
    
    if not args.username or not args.password:
        raise ValueError("Username and password must be provided via --username/--password or OPENREVIEW_USERNAME/OPENREVIEW_PASSWORD env vars")

    client = openreview.api.OpenReviewClient(
        baseurl="https://api2.openreview.net", username=args.username, password=args.password
    )

    venue_group = client.get_group(args.venue_id)
    submission_name = venue_group.content["submission_name"]["value"]
    submissions = client.get_all_notes(
        invitation=f"{args.venue_id}/-/{submission_name}", details="replies"
    )

    with open(args.output_file, "wb") as file:
        pickle.dump(submissions, file)

if __name__ == "__main__":
    main()
