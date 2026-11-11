# Door context: configuration and limits

Select contacts through the existing room source editor. Configure each contact in the same **Windows, doors, ventilation and shading** category below the Eco switch. The contact must remain assigned to its original native HA Area; the optional second endpoint is another configured Area, not an entity reassignment. Room names may change without breaking links.

## Defaults
Connections are absent, purpose is Interior, and report timeout is 0 (event-only). Explicitly mark any fire/safety or exterior door. HEM never moves a door/lock, obstructs required ventilation, recommends propping a fire door, or claims that a closed contact proves isolation. Exterior classification withdraws the interior target. Invalid/moved targets remain visible for correction and supply no graph path.

A reporting timeout is **not** a door-open timer. Enable it only if the source has a documented regular reporting cadence. HEM uses last_reported (last_updated fallback), not last_changed. Unavailable/restored/retyped/moved contacts cannot authorize closed-door Eco. An open contact alongside an unknown contact means at least one door is open, not complete room evidence.

## Passive decisions
CO₂ uses the configured indoor threshold, not a newly invented health limit. High CO₂ calls for assessing fresh-air ventilation, never turning on a particle purifier. Elevated humidity calls for assessing local extraction/dehumidification; existing controllers decide any physical action independently. Moisture-transfer cautions compare humidity ratios and projected relative humidity at the cooler room temperature. The operational screening margins (3°C difference, 0.5 g/kg moisture difference, projected RH ≥70%) are conservative product heuristics, not validated building-specific safety guarantees or medical limits.

A verified open-interior-door graph can show a possible route to an already open window only when current outdoor evidence is complete and safe. It never measures airflow, air changes, pressure balance, combustion safety or actual exchange through transfer grilles. Required background ventilation and building fire/combustion rules take precedence. A fire-door-open indication asks the user to follow the building rules; lawful automatic hold-open systems are not diagnosed as defective.

Door transitions are hints only. They never override an authoritative room list, home trackers, local presence, sleep or manual state. Several rapid transitions trigger a check-contact advisory. Activity while reported Away is not an intrusion diagnosis. Quiet context reports an already verified sleeping room behind a closed boundary; no Announcement Hub route or unrelated notification policy is changed.

## Performance and privacy
One bounded monitor belongs to each HEM entry. At most 128 graph contacts, 32 recent transitions per tracked contact, and 240 samples per open/closed thermal regime are retained in memory. Histories reset on restart, membership/measurement changes and invalid clock movement. Existing capture/tick scheduling is reused; no dedicated polling loop or database of occupant movement is added. Samples are descriptive and confounded by weather, HVAC and occupancy; they are not an energy-savings or thermal-conductance model. New HA diagnostic entities expose a small bounded summary; normal HA recorder/privacy settings still apply.

## Evidence sources
- Home Assistant state-object timestamps: https://www.home-assistant.io/docs/configuration/state_object
- Umweltbundesamt, heating and mould avoidance: https://www.umweltbundesamt.de/themen/gesundheit/umwelteinfluesse-auf-den-menschen/schimmel/richtig-heizen-schimmelbildung-vermeiden
- US EPA, residential air cleaners: https://www.epa.gov/indoor-air-quality-iaq/guide-air-cleaners-home
- University of Melbourne, air-cleaner/CO₂ distinction: https://sgeas.unimelb.edu.au/engage/air-cleaner-guide/frequently-asked-questions

The source guidance supports the distinctions above; HEM's numeric screening margins, memory bounds and UI choices are engineering decisions. No external source validates this implementation as a complete ventilation or life-safety controller.
