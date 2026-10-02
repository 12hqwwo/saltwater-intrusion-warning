# TLCN review checklist

- Is EC kept in mS/m?
- Is any `salinity` label incorrectly used for EC?
- Is there a fixed EC→salinity conversion?
- Is a monthly target being upsampled to daily?
- Is GloFAS extracted from a defensible grid/reach?
- Are DAHITI and tide kept distinct?
- Are pending gates represented without fake coordinates?
- Does SQL target the intended database and support rollback?
- Are raw inputs unchanged?
- Are source/hash/unit/time/CRS details preserved?
- Is validation chronological for time series?
- Does documentation describe actual implementation rather than target architecture?
