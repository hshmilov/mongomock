-- This SQL creates important functions used by axonius postgres

/*
    add_cycle_partitions adds all cycle partitioned tables with given cycle id
 */
CREATE OR REPLACE FUNCTION add_cycle_partitions(cycle_id int)
  RETURNS VOID AS
$func$
DECLARE
	_relname text;
BEGIN
	FOR _relname IN (SELECT distinct on(relname) relname FROM pg_inherits
					JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
					WHERE relhasindex = True)
		LOOP
			EXECUTE format('CREATE TABLE %1$s_cycle_%2$s PARTITION OF %1$s FOR VALUES IN (%2$s);', _relname, cycle_id);
		END LOOP;
	RETURN;
END
$func$ LANGUAGE plpgsql;


/*
    removes_cycle_partitions deletes all cycle partitioned tables with given cycle id
 */
CREATE OR REPLACE FUNCTION remove_cycle_partitions(cycle_id int)
  RETURNS VOID AS
$func$
DECLARE
	_relname text;
BEGIN
	FOR _relname IN (SELECT distinct on(relname) parent.relname FROM pg_inherits
					JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
					WHERE relhasindex = True)
		LOOP
			PERFORM format('DROP TABLE %1$s_cycle_%2$s;', _relname, cycle_id);
		END LOOP;
	RETURN;
END
$func$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION add_lifecycle(_fetch_time bigint)
RETURNS INT AS
$func$
BEGIN
	IF NOT (EXISTS (SELECT 1 FROM lifecycle as lc WHERE lc.fetch_time = _fetch_time LIMIT 1)) THEN
	 INSERT INTO lifecycle (fetch_time) VALUES (_fetch_time);
	 RETURN (SELECT id from lifecycle order by id desc limit 1);
	END IF;
	RETURN -1;
END
$func$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION prune_partitions(_fetch_cycle int)
RETURNS VOID AS
$func$
BEGIN
    FOR i IN 1.._fetch_cycle LOOP
        PERFORM remove_cycle_partitions(i);
    END LOOP;
END
$func$ LANGUAGE plpgsql;

-- Devices

/*
    rebuild device rebuilds the device based on its currently linked devices
 */
CREATE OR REPLACE FUNCTION rebuild_device(_device_id uuid, _fetch_cycle int)
RETURNS VOID AS
$func$
BEGIN
    IF EXISTS (SELECT 1 from adapter_devices as ad where ad.device_id = _device_id and ad.fetch_cycle = _fetch_cycle) THEN
        INSERT INTO devices (id, fetch_cycle, hostnames, adapter_names, adapter_count, last_seen)
        (SELECT _device_id as id , _fetch_cycle as fetch_cycle,
                array_agg(distinct hostname ORDER BY hostname desc) FILTER (WHERE hostname IS NOT NULL) as hostnames,
                array_agg(distinct adapter_name ORDER BY adapter_name desc) FILTER (WHERE adapter_name IS NOT NULL) as adapter_names,
                count(distinct adapter_id) as adapter_count, max(last_seen) as last_seen
        FROM adapter_devices where device_id = _device_id and fetch_cycle = _fetch_cycle)
        ON CONFLICT (id, fetch_cycle) DO UPDATE
        SET hostnames = excluded.hostnames,
            adapter_count = excluded.adapter_count,
            adapter_names = excluded.adapter_names,
            last_seen = excluded.last_seen;
    ELSE
        DELETE FROM devices as u where u.id = _device_id and u.fetch_cycle = _fetch_cycle;
    END IF;
END
$func$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION relink_adapter_device()
RETURNS TRIGGER AS
$func$
BEGIN
	IF OLD.device_id IS NOT NULL THEN
	    PERFORM rebuild_device(OLD.device_id, NEW.fetch_cycle);
	END IF;
	IF NEW.device_id IS NOT NULL THEN
	    PERFORM rebuild_device(NEW.device_id, NEW.fetch_cycle);
	END IF;
RETURN NEW;
END
$func$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_device
    AFTER UPDATE OF device_id OR INSERT ON adapter_devices
    FOR EACH ROW
    EXECUTE PROCEDURE relink_adapter_device();


-- Users

/*
    rebuild device rebuilds the device based on its currently linked devices
 */
CREATE OR REPLACE FUNCTION rebuild_user(_user_id uuid, _fetch_cycle int)
RETURNS VOID AS
$func$
BEGIN
        IF EXISTS (SELECT 1 from adapter_users as au where au.user_id = _user_id and au.fetch_cycle = _fetch_cycle) THEN
            INSERT INTO users (id, fetch_cycle, usernames, adapter_names, adapter_count, last_seen)
            (SELECT _user_id as id , _fetch_cycle as fetch_cycle,
                    array_agg(distinct username ORDER BY username desc) FILTER (WHERE username IS NOT NULL) as usernames,
                    array_agg(distinct adapter_name ORDER BY adapter_name desc) FILTER (WHERE adapter_name IS NOT NULL) as adapter_names,
                    count(distinct adapter_id) as adapter_count, max(last_seen) as last_seen
            FROM adapter_users where user_id = _user_id and fetch_cycle = _fetch_cycle)
            ON CONFLICT (id, fetch_cycle) DO UPDATE
            SET usernames = excluded.usernames,
                adapter_names = excluded.adapter_names,
                adapter_count = excluded.adapter_count,
                last_seen = excluded.last_seen;
        ELSE
            DELETE FROM users as u where u.id = _user_id and u.fetch_cycle = _fetch_cycle;
        END IF;
END
$func$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION relink_user()
RETURNS TRIGGER AS
$func$
BEGIN
	IF OLD.user_id IS NOT NULL THEN
	    PERFORM rebuild_user(OLD.user_id, NEW.fetch_cycle);
	END IF;
	IF NEW.user_id IS NOT NULL THEN
	    PERFORM rebuild_user(NEW.user_id, NEW.fetch_cycle);
	END IF;
RETURN NEW;
END
$func$ LANGUAGE plpgsql;


CREATE TRIGGER trigger_update_user
    AFTER UPDATE OF user_id OR INSERT ON adapter_users
    FOR EACH ROW
    EXECUTE PROCEDURE relink_user();


-- This sql creates a table function view allowing to access a table with params

CREATE OR REPLACE FUNCTION device_network_interfaces(_deviceId uuid, _fetchCycle int)
  RETURNS TABLE (deviceId uuid, fetch_cycle int, mac_addr macaddr, ip_addrs inet[]) AS
$func$
    SELECT distinct on (ip_addrs, mac_addr) * from network_interfaces
    where device_id = ANY(select id from adapter_devices where device_id = $1 and fetch_cycle = $2) and fetch_cycle = $2;
$func$ LANGUAGE sql;


CREATE OR REPLACE FUNCTION device_tags(_deviceId uuid, _fetchCycle int)
  RETURNS TABLE (name text, creator text, level text) AS
$func$
    SELECT distinct on (ad_tags.adapter_device_id, ad_tags.name) t.name, t.creator, t.level FROM adapter_device_tags as ad_tags
    LEFT JOIN tags t ON (ad_tags.name = t.name)
    WHERE ad_tags.adapter_device_id = ANY(select id from adapter_devices ad where ad.device_id = $1 and ad.fetch_cycle = $2);
$func$ LANGUAGE sql;

--
CREATE OR REPLACE FUNCTION arrayToText(arr text[]) RETURNS text AS $$
   SELECT arr::text
$$ LANGUAGE SQL IMMUTABLE;

-- Helpful functions
CREATE OR REPLACE FUNCTION family(inet[])
RETURNS int[]
AS
$$
DECLARE
   arrInets ALIAS FOR $1;
   retVal float[];
BEGIN
   FOR I IN array_lower(arrInets, 1)..array_upper(arrInets, 1) LOOP
    retVal[I] := family(arrInets[I]);
   END LOOP;
RETURN retVal;
END;
$$
LANGUAGE plpgsql
   STABLE
RETURNS NULL ON NULL INPUT;