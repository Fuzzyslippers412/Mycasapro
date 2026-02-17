========================================================
USDC USER FLOWS + SONIC SECURITY FLOWS (VALUE CAPTURE WITHOUT UX CONFUSION)
========================================================

GOAL
- Users deposit/withdraw/win in USDC (or stable) with clean expectations.
- Protocol still captures value for Sonic by making Sonic the REQUIRED security substrate:
  - bonds
  - slashing
  - finality
  - "official" ecosystem gating
- Avoid Polygon failure mode: apps succeed while token demand is optional/bypassable.

CORE RULE (FREEZE THIS)
1) USER MONEY (ENTRY + PAYOUT) = USDC ONLY
2) PROTOCOL SECURITY / FINALITY / LEGITIMACY = SONIC BONDS (NATIVE TOKEN)
3) USERS NEVER EXPECT SONIC BACK FOR A USDC DEPOSIT

========================================================
A) USER EXPERIENCE (WHAT USERS SEE)
========================================================

User deposits:
- USDC in
User plays:
- predictions in league fixtures
User winnings:
- USDC out
User withdrawals:
- USDC out (minus exit fee if applicable)

User NEVER needs:
- Sonic balance
- Sonic wallet funding for gameplay (optional: gas sponsor)
- Sonic exposure for payouts

========================================================
B) WHERE SONIC IS USED (WHAT PROTOCOL REQUIRES)
========================================================

Sonic is REQUIRED ONLY for "security-critical" actions:
- creating events used for settlement
- proposing outcomes
- challenging outcomes
- finalizing standings roots
- publishing official templates / modules (ecosystem legitimacy)

Sonic is NOT used for:
- entry fees
- prize pool custody
- payout calculations
- fee payouts to creators/platform (v1)
(All USDC to keep expectations consistent)

========================================================
C) CONTRACT-BY-CONTRACT MAPPING
========================================================

----------------------------------------
1) PrizeVault (USDC ONLY)
----------------------------------------

Purpose:
- Hold only prize pool funds (activePool) in USDC
- Pay winners in USDC
- Withdraw refunds in USDC
- No Sonic involvement

Key invariants:
- PrizeVault NEVER touches Sonic
- PrizeVault NEVER pays creator/platform fees
- PrizeVault uses StandingsFinalizer FINAL root for rank claims

Join:
- user pays entryFee in USDC
- vault forwards feeReservePerUser USDC to FeeVault
- vault adds prizeContributionPerUser USDC to activePool

Withdraw:
- refunds only prizeContributionPerUser USDC (not feeReserve)
- takes exit fee in USDC -> forwards to FeeVault
- sets payoutForfeited = true forever

Claim:
- requires StandingsFinalizer FINAL root
- requires valid Merkle proof for rank
- pays deterministic payout in USDC from finalPoolSnapshot

----------------------------------------
2) FeeVault (USDC ONLY)
----------------------------------------

Purpose:
- Hold ALL non-prize money in USDC:
  - fee reserves forwarded on join
  - exit fees forwarded on withdraw
- Pay:
  - creators (USDC)
  - platform treasury (USDC)

Key invariant:
- FeeVault NEVER pays prizes
- FeeVault only pays deltas based on SeasonLeague counters

Claims:
- creator claim:
    amount = SeasonLeague.creatorFeesAccrued[creator] - creatorFeesPaid[creator]
- platform claim:
    amount = SeasonLeague.platformFeesAccrued - platformFeesPaid
- exit fee claim:
    amount = exitFeesAccrued - exitFeesPaid

----------------------------------------
3) SeasonLeague (USDC ACCOUNTING, SONIC-NEUTRAL)
----------------------------------------

Purpose:
- Maintain:
  - participants (joined/withdrawn flags)
  - fixtures registry
  - fee accrual counters (numerical amounts in USDC units)
  - scoring stats (points/correct/played etc.)
- Enforce module authorization:
  - only registered module can notifyPredictionPlaced and markFixtureFinal

Key notes:
- SeasonLeague does NOT hold funds.
- Fee amounts are tracked in USDC units even if Sonic is used elsewhere.

----------------------------------------
4) StandingsFinalizer (SONIC BONDS)
----------------------------------------

Purpose:
- Publish FINAL standings root (Merkle root) for payouts.
- Security via bonds + disputes.

Required Sonic logic:
- proposeRoot requires msg.value >= minRootBondSonic
- challengeRoot requires msg.value >= proposerBond (or >= min)
- slashing:
  - incorrect proposer loses bond
  - incorrect challenger loses bond
- arbiter resolves disputes

Why this matters:
- Payout finality is now protected by Sonic.
- As seasons scale, roots become high-value targets -> Sonic bonds scale too.

Key interface:
- getFinalRoot(seasonLeague) -> (finalized, root)
- verifyRankProof(...) helper

----------------------------------------
5) EventFactory (SONIC CREATOR BONDS)
----------------------------------------

Purpose:
- Strict template event creation:
  - sports results
  - yes/no events
- Prevent spam + ambiguity.

Required Sonic logic:
- createEvent requires:
    msg.value >= creatorBondMinSonic (+ optional creationFeeSonic)
- bond policy:
  - refunded if event resolves cleanly
  - slashable if event is malformed / spam / repeatedly disputed
  - optional: bond returned only after oracle finalizes

Why:
- High event volume locks Sonic.
- Forces event creators to have skin in the game.

----------------------------------------
6) EventOracleAdapter (SONIC BONDS + SLASHING)
----------------------------------------

Purpose:
- Optimistic oracle for event outcomes:
  - propose result
  - challenge result
  - finalize if unchallenged
  - arbiter resolves if disputed

Required Sonic logic:
- proposeResult payable:
    msg.value >= minProposalBondSonic
- challengeResult payable:
    msg.value >= proposalBond (or min)
- slashing:
  - loser bond slashed to treasury/burn/distributed (policy)
  - winner receives combined bonds

Why:
- The "truth layer" of sports fixtures is now Sonic secured.
- This is the key thing Polygon did NOT enforce for Polymarket.

----------------------------------------
7) Fixture Modules (USDC USER FLOW, SONIC-NEUTRAL)
----------------------------------------

Crypto module:
- commit/reveal predictions
- snapshots prices
- computes UP/DOWN/FLAT outcome deterministically
- notifies SeasonLeague to accrue USDC fees
- finalize -> SeasonLeague.markFixtureFinal

Sports module:
- commit/reveal predictions
- reads EventOracleAdapter FINAL outcome
- notifies SeasonLeague to accrue USDC fees
- finalize -> SeasonLeague.markFixtureFinal

Note:
- modules themselves do not require Sonic for users.
- only proposers/challengers/finalizers in oracle/finalizer require Sonic.

----------------------------------------
8) LeagueFactory (SONIC BONDS FOR LEGITIMACY)
----------------------------------------

Purpose:
- Avoid "Polygon mode" where builders can profit without holding chain risk.
- Make "official" ecosystem surfaces require Sonic bonding.

Recommended Sonic gating:
A) Template publishing bond
- publishTemplate(...) payable
- msg.value >= templateBondSonic
- templates without bond exist but are "unofficial"
- UI lists "official" by default

B) Module registration bond
- registerModule(module) payable
- msg.value >= moduleBondSonic
- slash bond if module exploited / malicious

Why:
- Builders must be long Sonic to gain distribution.
- Spam templates/modules become expensive.

========================================================
D) WHY THIS AVOIDS POLYGON FAILURE (MECHANISTIC)
========================================================

Polygon failure mode:
- Apps can scale with stablecoins + abstractions
- Token is optional; value capture is narrative-based

Our design:
- Users = USDC only (best UX)
- Protocol integrity = Sonic bonds
- Scale increases:
  - event volume => Sonic locked in EventFactory bonds
  - resolution volume => Sonic bonded in EventOracleAdapter
  - season volume => Sonic bonded in StandingsFinalizer
  - ecosystem growth => Sonic bonded in LeagueFactory template/module bonds

Result:
- It becomes impossible to run the system at scale without locking Sonic.
- But users never have to touch Sonic.

========================================================
E) MINIMUM REQUIRED CHANGES (IF WE WANT 80/20)
========================================================

Must implement Sonic bonds in:
1) EventFactory.createEvent (creatorBondMinSonic)
2) EventOracleAdapter.propose/challenge (minProposalBondSonic)
3) StandingsFinalizer.propose/challenge (minRootBondSonic)
4) LeagueFactory.publishTemplate + registerModule (bonded "official")

Keep USDC-only for:
- PrizeVault
- FeeVault
- all user-facing deposits/payouts

========================================================
F) PARAMETERS TO SET (PRODUCTION GUIDANCE)
========================================================

Sonic bond params (set meaningful but not insane):
- creatorBondMinSonic: enough to deter spam events
- minProposalBondSonic: enough to deter wrong proposals
- minRootBondSonic: enough to deter fake standings roots
- templateBondSonic: enough to deter spam templates
- moduleBondSonic: enough to deter malicious modules

Window params:
- EventOracle challengeWindowSeconds: 2h-24h depending on risk
- StandingsFinalizer challengeWindowSeconds: 6h-24h

Slashing policy:
- send slashed Sonic to:
  a) platform treasury OR
  b) burn OR
  c) validator/staker rewards
Pick one and freeze.

========================================================
G) BUILDER TASK LIST (IMPLEMENTATION ORDER)
========================================================

Phase 1 (USDC core)
- PrizeVault USDC join/withdraw/claim invariants
- FeeVault USDC deposits + fee claims
- SeasonLeague fee counters and module authorization
- LeagueFactory season/template basics

Phase 2 (Sonic security)
- Add Sonic bond requirements:
   EventFactory
   EventOracleAdapter
   StandingsFinalizer
   LeagueFactory template/module bonds
- Add slashing + arbiter wiring
- Add tests:
   - wrong proposer loses Sonic
   - wrong challenger loses Sonic
   - no finalize without windows

Phase 3 (end-to-end)
- Deploy on Sonic testnet
- Run:
  join -> play -> resolve -> finalize root -> claim USDC
  plus:
  dispute flows with Sonic bonds

========================================================
END WRITEUP
========================================================
