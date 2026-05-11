PLG What-if setup guide (from BPI2017 happy path)

1) Use plg_activity_nodes.csv to create activities in PLG.
2) Use plg_happy_edges.csv to connect transitions with probabilities.
3) For activity/service time parameterization:
   - Use median_wait_min as baseline.
   - Use p90_wait_min for stress scenario.
4) Recommended what-if scenarios:
   S1: Reduce waits on top 2 edges by 20% and compare cycle time.
   S2: Increase branch probability toward rework edges by +10%.
   S3: Shift New credit segments to stricter early validation gate.
5) Evaluate simulated log with same pipeline: conformance, bottleneck, non-success prediction.