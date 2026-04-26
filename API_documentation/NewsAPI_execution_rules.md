## Usage Rules
- ALWAYS speficy for <= 20 days from current date and time. 
- Default endpoint: /v2/everything
- Use /v2/top-headlines only for real-time UI display
- Always include:
  - language=en
  - sortBy=publishedAt
- Always paginate until:
  - pageSize < requested OR
  - max_pages reached

Mandatory output format:
{
  "title": string,
  "source_name": string,
  "source_id": string | null,
  "author": string | null,
  "published_at": ISO8601,
  "url": string,
  "description": string | null,
  "content": string | null
}

## Error Handling

- 429 → retry after delay
- 500 → retry up to 3 times
- 401 → fail immediately
- empty results → continue pipeline, do not crash

