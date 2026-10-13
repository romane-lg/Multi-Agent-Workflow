# V2.2 pilot comparison

Inclusive window: 2024-10-10 through 2026-10-09. Same seed, eight balanced company/dimension opportunities, beverage_and_food_trade domains, no pagination. No publisher fetches.

New query rules: uniformly retain the quoted company and add intitle:"{company}"; products use (launch OR launches OR "new products" OR flavor OR flavour).
New entity rules: title confirmation; Culture Pop title match on approved beverage/food trade domains supplies context; URL/snippet-only evidence requires review. Existing date/exclusion rules retain precedence.

| Company | Dimension | Original returned / accepted / rejected / review | Revised returned / accepted / rejected / review |
|---|---|---|---|
| Olipop | products | 13 / 3 / 10 / 0 | 16 / 13 / 3 / 0 |
| Olipop | business | 73 / 12 / 61 / 0 | 14 / 12 / 2 / 0 |
| Poppi | products | 17 / 2 / 15 / 0 | 20 / 17 / 3 / 0 |
| Poppi | business | 86 / 15 / 71 / 0 | 19 / 16 / 2 / 1 |
| Culture Pop | products | 6 / 0 / 6 / 0 | 21 / 11 / 10 / 0 |
| Culture Pop | business | 48 / 5 / 40 / 3 | 11 / 8 / 3 / 0 |
| Zevia | products | 13 / 1 / 12 / 0 | 10 / 10 / 0 / 0 |
| Zevia | business | 87 / 10 / 77 / 0 | 10 / 10 / 0 / 0 |

Eight API requests made for the revised pilot: eight HTTP 200 responses, no retries, errors or rate limits. Original history contains nine recorded attempts, including an interrupted request whose charge is unknown.

Occurrence acceptance: 48/343 (14.0%) -> 97/121 (80.2%). Unique URL acceptance: 43/244 (17.6%) -> 52/67 (77.6%). All 43 original accepted URLs retained; nine additional accepted URLs.

Culture Pop products: six returned, zero accepted -> 21 returned, 11 accepted, ten rejected. Product-relevant titles include the Apple soda roundup, Sparkling Apple limited edition, Raspberry Lemonade launch and Black Cherry collaboration. Query membership is not verified topic classification.

Accepted publishers: BevNET 34 -> 41; FoodBev 7 -> 9; FoodNavigator-USA 2 -> 2; BeverageIndustry 0 -> 0. BevNET accepted share: 79.1% -> 78.8%. Returned publisher occurrences: BevNET 257 -> 99; FoodBev 31 -> 16; FoodNavigator-USA 55 -> 6.

Duplicate URLs: 71 -> 50; extra associations: 99 -> 54; accepted URLs with multiple associations: 10 -> 45. All 121 occurrences are retained as associations on 67 URL records. Zevia products and business yield the same ten accepted URLs.

Potential relevance false positives: "Crooked Pop Taps Former Zevia Exec Lee Schill as CCO" and "Investors of Poppi, Goodles raise seed round for powdered beverage startup" mention the target but concern another company. Topic spillover includes Poppi acquisition results in products and Zevia campaign/management results in products. These demonstrate secondary connections and weak topic separation rather than failed name matching.

The Poppi URL-only PepsiCo snack-pricing result is review, not accepted. All three former Culture Pop review titles are accepted in the revised business query. Culture Pop product results still include seven out-of-window occurrences; local filtering rejects them.

Recommendation: proceed to the full V2.2 collection only after separate approval, for a title-confirmed company evidence pool. Keep dimensions as provenance and inspect secondary-company mentions during evidence selection. No full collection has run.

Validation: 14 offline tests passed; balanced query schedule, manifest/code hashes, association totals and HTTP attempts checked. Every pre-existing news_scrapper file matches its recorded SHA-256. V1, original V2, extraction and CrewAI were not modified. No commit or push.

Limitations: acceptance is rule eligibility, not measured ground-truth precision. No body verification or recall estimate. Other source groups remain untested. Query and entity revisions were tested together; attribution to an individual change is not possible.
