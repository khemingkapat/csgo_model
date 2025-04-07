# ESTA CSGO Data Modelling
This project Featured in CPE232 Data Models, KMUTT

# Structure
> some point that could be noted, maybe plan to move to sql database for easier access

## Root Data
data such as `mapName`, `tickRate`, etc. Easy to access

## gameRounds
uniquely identify by number of round (started by $0$) with important data on
- `startTick` and `endTick`
- `tScore`, `ctScore` and anything related to score
- `tTeam` and `ctTeam` as name of team
- `roundEndReason`, the reason why the round end **important**
### kills
detail about each kill in that round, uniquely identify with number of round, started with 0.

with important informatino such as
- Location of attacker and victim
- Kill assist, flash assist
- Weapon
- Type, `noScope`, `thruSmoke`, `wallBang`

### Damage
almost the same as kills, but quite more detail specific to damage.
- `hpDamage`,`armorDamage`, `hitGroup`

### grenades
same basic info as kills, with `grenadeType` and location

### bombEvents
the time, location, of bomb such as planting

### weaponFires
I think it is bullet fires, including grenades that like an action

### flashes
flashing information

### frames
infor about each frame, is that `isKillFrame` and like more, also information and action about that player.

