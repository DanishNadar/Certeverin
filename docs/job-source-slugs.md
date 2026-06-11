# Job Source Slugs

## Greenhouse

Greenhouse public job listings do not need an API key for GET requests. Certeverin needs the public board slug from a Greenhouse jobs URL.

Example URL:

```text
https://boards.greenhouse.io/stripe
```

Slug:

```text
stripe
```

Small list:

```bash
GREENHOUSE_BOARD_SLUGS=stripe,databricks
```

Large list:

```bash
GREENHOUSE_BOARD_SLUGS_FILE=shared/job_sources/greenhouse_board_slugs.txt
```

## Lever

Lever public postings do not need the private Lever Data API key. Certeverin needs the public company slug from a Lever jobs URL.

Example URL:

```text
https://jobs.lever.co/leverdemo
```

Company slug:

```text
leverdemo
```

Small list:

```bash
LEVER_COMPANY_NAMES=leverdemo,netflix
```

Large list:

```bash
LEVER_COMPANY_NAMES_FILE=shared/job_sources/lever_company_names.txt
```

## Large Lists

For thousands or tens of thousands of companies, use the file variables instead of putting everything in `.env`.

Files can contain one slug per line, comma-separated rows, comments, blank lines, or full URLs:

```text
# accepted
stripe
https://boards.greenhouse.io/databricks
leverdemo,netflix
```

Certeverin deduplicates repeated entries before fetching.
