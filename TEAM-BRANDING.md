# Manual team branding

Edit `frontend/src/team-branding.json`. Keys are stable ESPN team IDs, never names. The live configuration starts empty; no colors have been invented. Example only (not active):

```json
{
  "teams": {
    "11": [
      { "startSeason": 2021, "endSeason": 2023, "primaryColor": "#D92332" },
      { "startSeason": 2024, "endSeason": 2025, "primaryColor": "#2864DC", "logoOverride": "team-logos/team-11-2024.png" },
      { "startSeason": 2026, "primaryColor": "#1A9F54" }
    ]
  }
}
```

To retain the automatic ESPN logo, specify only `primaryColor`. To override a logo, add `logoOverride` and put the actual image in `frontend/public/team-logos/`. PNG, JPG, JPEG, WebP and SVG are supported. Local URLs honor the deployment base path. The display tries the manual image, then the existing generated logo, then the existing initial fallback.

Ranges are inclusive. Omit `endSeason` to continue indefinitely, avoiding yearly duplication. Ranges may have gaps but cannot overlap. Fields do not carry across ranges: a color-only period following a logo override returns to the existing automatic logo. Missing colors use Pocky green (`#1a9f54`); colors are never extracted from images. Logo-only periods are also allowed. All-Time selects the period with the greatest startSeason, even for teams no longer present in the current league. It does not combine historical colors or inherit omitted fields from older periods.

Historical Teams and Standings resolve their selected season. Record Book resolves the selected season or All-Time consistently. H2H summary uses All-Time branding; season-filtered comparisons use that season. The shared resolver accepts any team ID, including IDs absent from the current season. Names and league membership continue to come from the existing historical contracts. This does not introduce a new franchise identity policy.

`leagues.json` and its current-season `teamLogoOverrides` remain unchanged (currently empty). Existing generated logos remain the fallback, including any legacy manual override. No images were downloaded or replaced. Branding is applied at display time; the season, H2H and Record Book JSON contracts are unchanged, and rebuilding the frontend picks up edits without fetching ESPN again. Colors are available through `resolveTeamBranding()` but are not applied to page styling yet.

Run the frontend tests and build after editing. Validation rejects malformed IDs, ranges, hex colors and image paths; ensure any referenced image file actually exists.

## Observed ESPN identities, 2021–2026

These are observed names, not inferred color/logo periods. No manual branding periods are configured yet.

- **1**: 2021: Amazon Rockets; 2022: Beans Greens; 2023: Taking a Schult; 2024: ATN Network; 2025: Brian's Original Fried Haddock; 2026: Brian's Original Fried Haddock
- **2**: 2021: Light Work; 2022: Light Work; 2023: Light Work; 2024: Slim Pickens; 2025: Reckless Drivers; 2026: Juwan's Team
- **3**: 2021: Michigander at these Nuts; 2022: Michigander at these Nuts; 2023: Christian's Children; 2024: Double Kupp; 2025: Bowers' Castle; 2026: Good Christians Hate Sinners
- **5**: 2021: New Jersey Eren; 2022: New Jersey Eren; 2023: Eren's Fantasy Football Team; 2024: Bosh Champ; 2025: Mr. Gibbs; 2026: The Concep
- **6**: 2021: Its Bigger Than Black or White✊; 2022: Its Bigger Than Black or White✊; 2023: Njigbas in Paris; 2024: Tee Time; 2025: if u got me get rid of me; 2026: LOVE MEEEE
- **7**: 2021: Certified Boy Lover; 2022: 90%ofGamblersQu itbeforehitting; 2023: 180 Buccs
- **9**: 2021: Turkey Eren; 2022: Turkey Eren; 2023: Turkey Eren
- **10**: 2021: Dookey  Kong; 2022: Dookey  Kong
- **11**: 2021: Cheese Touch; 2022: Cheese Touch; 2023: Cheese Touch; 2024: Cheese Touch; 2025: Cheese Touch; 2026: Choose Olave
- **12**: 2021: semanto gay and kissed allen; 2022: semanto gay and kissed allen; 2023: semanto gay and kissed allen; 2024: semanto gay and kissed allen; 2025: semanto gay and kissed allen; 2026: semanto gay and kissed allen
- **13**: 2022: The Trenches PerryG; 2023: The Trenches PerryG; 2024: The Trenches PerryG; 2025: The Trenches PerryG; 2026: The Trenches PerryG
- **14**: 2022: Week 14's  Biggest Loser
- **15**: 2022: Team Liou; 2023: Team Liou; 2024: Team Liou; 2025: Team Liou; 2026: Gibb me dak
- **16**: 2022: Dolla Dolla Bills Y'all; 2023: Jalapeno Kittle Chips; 2024: For Kyren Out Loud; 2025: CMC; 2026: Eat the Booty Like Groceries
