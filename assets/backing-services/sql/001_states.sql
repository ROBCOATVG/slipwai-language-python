-- The state-stored rung's one table: current state per id, and the version a save is guarded by.
--
-- No log behind it and no projection to be behind: a read model on this rung is a query over these
-- rows. The version starts at 0 with the first save and moves on by exactly one with every save after
-- it; `repository_postgres.py` compares and increments it in one statement. The state is a JSON
-- object, which the port checks before it writes and this checks for whatever writes next.
CREATE TABLE states (
  id      TEXT    PRIMARY KEY,
  version INTEGER NOT NULL CHECK (version >= 0),
  state   JSONB   NOT NULL CHECK (jsonb_typeof(state) = 'object')
);
