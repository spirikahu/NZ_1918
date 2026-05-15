# Task
I have provided a table of all school names. I want to identify which county or borough each school was in for the entire .csv file. These are names that were in the Southland Education District of New Zealand in 1918. Use your search tool.

# Context
Southland Education District in 1918 included schools located across Southland County, Wallace County, Invercargill Borough, Gore Borough, and adjacent rural localities. Many schools were named after railway sidings, valleys, or small settlements rather than legally defined towns. Railway lines and post office localities are often stronger indicators of county membership than school names alone.

When matching school names:
- prefer exact locality matches
- then railway station matches
- then valley/river/locality matches
- avoid assuming nearest modern town
- prefer historical locality evidence over modern geography

# Output Schema:
The output scheme should look like:
| school | county_borough | evidence | confidence | locality - nearest town, village, etc (optional) | town_district(optional) | Notes |

# Rules
- Optimize precision. It is most important that confidence levels and estimates of county / borough are done accurately.
- Nearest borough is acceptable when locality is ambiguous. When this fallback is used it should be mentioned in the 'evidence' section.
- Evidence is mandatory. Point to sections if possible. 

# Confidence scale
Confidence scales should be given as
- High
- Medium
- Low
- Unresolved.
This should be based on the fuzzy matching of names, how much information was available, and how many competing candidates there were.

