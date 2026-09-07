# ColdChainGuard -- Operational RFM Asset Segmentation Insights

## Methodology
Entity segmented: **Vehicle** (vehicle_id)

| Dimension | Definition | Direction |
|-----------|-----------|-----------|
| R (Recency) | Days since vehicle's most recent shipment | Lower = better |
| F (Frequency) | Number of shipments handled | Higher = better |
| M (Volume) | Total product quantity transported | Higher = better |

> **Note on M adaptation:** Standard RFM uses monetary transaction value.
> ColdChainGuard does not record per-shipment revenue.
> M is adapted to transported product volume (sum of batch_quantity).
> This is a valid and documented adaptation for asset/operational segmentation.

Reference date: 2026-08-07
Total vehicles analysed: **100**

## Segment Summary
- **Champions**: 18 vehicles (18.0%) | Avg Recency: 0.0 days | Avg Frequency: 7.0 shipments | Avg Volume: 1214.0 units
- **Loyal Assets**: 35 vehicles (35.0%) | Avg Recency: 0.0 days | Avg Frequency: 6.7 shipments | Avg Volume: 1111.0 units
- **Active Assets**: 22 vehicles (22.0%) | Avg Recency: 0.2 days | Avg Frequency: 6.1 shipments | Avg Volume: 896.0 units
- **At-Risk Assets**: 5 vehicles (5.0%) | Avg Recency: 1.8 days | Avg Frequency: 1.2 shipments | Avg Volume: 131.0 units
- **Low-Activity Assets**: 20 vehicles (20.0%) | Avg Recency: 2.0 days | Avg Frequency: 0.0 shipments | Avg Volume: 0.0 units

## Key Findings
- **Largest segment**: Loyal Assets (35 vehicles, 35.0% of fleet)
- **Highest-frequency segment**: Champions (avg 7.0 shipments/vehicle)
- **Highest-volume segment**: Champions (avg 1214.0 units/vehicle)
- **Low / at-risk vehicles**: 25 vehicles need operational attention

## Operational Implications for Cold-Chain
- **Champions** are the fleet backbone: prioritise for preventive maintenance
  and compliance certification renewal.
- **Loyal Assets** should be monitored for any drop in frequency,
  which could indicate mechanical issues or route reassignment.
- **Active Assets** represent normal operational utilisation.
  Standard compliance monitoring is appropriate.
- **At-Risk Assets** show declining frequency.
  Investigate whether vehicles are awaiting maintenance or have been reassigned.
- **Low-Activity Assets** have minimal recent shipments.
  Consider whether these vehicles are retired, under repair,
  or require compliance certificate renewal before reactivation.

## Compliance Intersection
Vehicles in lower segments (At-Risk, Low-Activity) are more likely to have:
- Expired sensor calibration certificates (due to inactivity)
- Outdated compliance records
- Higher per-shipment excursion risk (equipment degradation during idle periods)

Cross-referencing RFM segments with compliance_results can identify
high-risk vehicles requiring immediate audit attention.