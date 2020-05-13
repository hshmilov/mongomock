--  TODO: Execute this on all tables to order columns in an optimal way
-- SELECT a.attname, t.typname, t.typalign, t.typlen
-- FROM pg_class c
--          JOIN pg_attribute a ON (a.attrelid = c.oid)
--          JOIN pg_type t ON (t.oid = a.atttypid)
-- WHERE c.relname = 'adapter_devices'
--   AND a.attnum >= 0
-- ORDER BY t.typlen DESC

-- Extensions:
CREATE EXTENSION pg_trgm;

CREATE TYPE adapter_type AS ENUM (
    'UNKNOWN',
    'CUSTOM',
    'ABSOLUTE',
    'ACTIVE_DIRECTORY',
    'AIRWATCH',
    'AIRWAVE',
    'ALERTLOGIC',
    'ALIBABA',
    'ANSIBLE_TOWER',
    'AQUA',
    'ARISTA_EOS',
    'ARMIS',
    'ARSENAL',
    'ARUBA',
    'AUTOMOX',
    'AWS',
    'AZURE_AD',
    'AZURE',
    'BAMBOOHR',
    'BIGFIX',
    'BIGFIX_INVENTORY',
    'BITDEFENDER',
    'BITLOCKER',
    'BITSIGHT',
    'BLACKBERRY_UEM',
    'BLUECAT',
    'BOMGAR',
    'CA_CMDB',
    'CA_SPECTRUM',
    'CARBONBLACK_DEFENSE',
    'CARBONBLACK_RESPONSE',
    'CENSYS',
    'CHECKPOINTR90',
    'CHEF',
    'CHERWELL',
    'CISCO',
    'CISCO_AMP',
    'CISCO_FIREPOWER_MANAGEMENT_CENTER',
    'CISCO_ISE',
    'CISCO_MERAKI',
    'CISCO_PRIME',
    'CISCO_STEALTHWATCH',
    'CISCO_UCM',
    'CISCO_UCSM',
    'CISCO_UMBERELLA',
    'CLAROTY',
    'CLEARPASS',
    'CLOUDFLARE',
    'CLOUD_PASSAGE',
    'CODE42',
    'COUNTER_ACT',
    'CROWD_STRIKE',
    'CSC_GLOBAL',
    'CSV',
    'CYBEREASON',
    'CYCOGNITO',
    'CYLANCE',
    'CYNET',
    'DATADOG',
    'DATTO',
    'DEEP_SECURITY',
    'DEFENDER_ATP',
    'DESKTOP_CENTRAL',
    'DEVICE42',
    'DIGICERT_CERTCENTRAL',
    'DIVVY_CLOUD',
    'DROPBOX',
    'DRUVA',
    'DUO',
    'DYNATRACE',
    'ECLYPSIUM',
    'EDGESSCAN',
    'ENDGAME',
    'ENSILO',
    'EPO',
    'ESET',
    'ESX',
    'F5_ICONTROL',
    'FIRE_EYE_HX',
    'FORCEPOINT',
    'FOREMAN',
    'FORTIGATE',
    'FRESH_SERVICE',
    'GCE',
    'GITHUB',
    'GOOGLE_BIG_QUERY',
    'GOOGLE_MDM',
    'GOTOASSIST',
    'GURDICORE',
    'GUARDIUM',
    'HASHICORP',
    'HAVEIBEENPWNED',
    'HP_NNMI',
    'HYPER_V',
    'IBM_TIVOLI_TADDM',
    'ICINGA',
    'IGAR',
    'ILLUSIVE',
    'IMPERVA',
    'INDEGY',
    'INFINITE_SLEEP',
    'INFOBLOX',
    'IVANTI_SM',
    'JAMF',
    'JSON',
    'JSON_FILE',
    'JUMPCLOUD',
    'JUNIPER',
    'JUNOS',
    'KASEYA',
    'KASPERSKY_SC',
    'LANDESK',
    'LANSWEEPER',
    'LIBERNMS',
    'LINUX_SSH',
    'LOGRYTHM',
    'MAAS360',
    'MALWAREBYTES',
    'MASSCAN',
    'MEDIGATE',
    'MEN_AND_MICE',
    'MINERVA',
    'MOBI_CONTROL',
    'MOBILE_IRON',
    'MSSQL',
    'NESSUS',
    'NESSUS_CSV',
    'NETBOX',
    'NETBRAIN',
    'NETSKOPE',
    'NEXPOSE',
    'NIMBUL',
    'NMAP',
    'NUTANIX',
    'OBSERVEIT',
    'OBSERVIUM',
    'OFFICE_SCAN',
    'OKTA',
    'OMNIVISTA',
    'OPENSTACK',
    'OPSWAT',
    'ORACLE_CLOUD',
    'ORACLE_VM',
    'ORCA',
    'PACKETFENCE',
    'PALOALTO_CORTEX',
    'PALOALTO_PANORAMA',
    'PALOALTO_XDR',
    'PKWARE',
    'PREEMPT',
    'PROMISEC',
    'PROXMOX',
    'PUPPET',
    'QCORE',
    'QUALYS',
    'QUEST_KACE',
    'RANDORI',
    'REDCANARY',
    'REDCLOAK',
    'REDSEAL',
    'RISK_IQ',
    'RIVERBED',
    'RUMBLE',
    'SALTSTACK',
    'SALTSTACK_ENTERPRISE',
    'SAMANGE',
    'SCCM',
    'SCEP',
    'SECDO',
    'SENTINELONE',
    'SERVICENOW',
    'SHOADAN',
    'SIGNALSCIENCES',
    'SKYBOX',
    'SNIPEIT',
    'SNOW',
    'SOFTLAYER',
    'SOLARWINDS_ORION',
    'SOPHOS',
    'SPACEWALK',
    'SPECOPS',
    'SPLUNK',
    'STRESSTEST',
    'SYMANTEC',
    'SYMANTEC_ALTIRIS',
    'SYMANTEC_CCS',
    'SYMANTEC_CLOUD_WORKLOAD',
    'SYMANTEC_DLP',
    'SYMANTEC_SEP_CLOUD',
    'SYSAID',
    'TANIUM',
    'TENABLE_IO',
    'TENABLE_SECURITY_CENTER',
    'TORIIHQ',
    'TRAIANA_LAB_MACHINES',
    'TRIPWIRE_ENTERPRISE',
    'TRUEFORT',
    'TWISTLOCK',
    'UNIFI',
    'VCLOUD_DIRECTOR',
    'WAZUH',
    'WEBROOT',
    'WEBSCAN',
    'WSUS',
    'ZABBIX',
    'ZSCALER',
    'NOZOMI_GUARDIAN',
    'FORCEPOINT_CSV'
);

-- Table: public.adapters

-- DROP TABLE public.adapters;

CREATE TABLE public.adapters
(
    id text NOT NULL,
    name text COLLATE pg_catalog."default",
    properties text[] COLLATE pg_catalog."default",
    CONSTRAINT adapters_pkey PRIMARY KEY (id)
);

ALTER TABLE public.adapters
    OWNER to postgres;

-- Table: public.devices

-- DROP TABLE public.devices;

CREATE TABLE public.adapter_devices
(
    id uuid NOT NULL,
    fetch_cycle int NOT NULL,
    hostname text COLLATE pg_catalog."default",
    name text COLLATE pg_catalog."default",
    type text COLLATE pg_catalog."default",
    domain text COLLATE pg_catalog."default",
    adapter_name text COLLATE pg_catalog."default",
    adapter_id text,
    device_id uuid,
    data jsonb,
    last_seen bigint,
    fetch_time bigint,
    os_id uuid,
    pretty_id text COLLATE pg_catalog."default",

    last_used_users text[],
    managed bool default false,
    part_of_domain bool default false,
    agent_version text COLLATE pg_catalog."default",
    agent_name text COLLATE pg_catalog."default",
    agent_status text COLLATE pg_catalog."default",

    model text COLLATE pg_catalog."default",
    manufacturer text COLLATE pg_catalog."default",
    serial text COLLATE pg_catalog."default",
    family text COLLATE pg_catalog."default",
    bios_version text COLLATE pg_catalog."default",
    bios_serial text COLLATE pg_catalog."default",

    CONSTRAINT adapter_devices_pkey PRIMARY KEY (id, fetch_cycle)
) PARTITION BY LIST (fetch_cycle);

ALTER TABLE public.adapter_devices
    OWNER to postgres;


-- Table: public.adapter_device_installed_software
-- DROP TABLE public.adapter_device_installed_software;

CREATE TABLE public.adapter_device_installed_software
(
 adapter_device_id uuid NOT NULL,
 fetch_cycle int NOT NULL ,
 name text COLLATE pg_catalog."default" NOT NULL,
 version text COLLATE pg_catalog."default" NOT NULL,
 PRIMARY KEY (adapter_device_id, fetch_cycle, version, name)
) PARTITION BY LIST (fetch_cycle);

ALTER TABLE public.adapter_device_installed_software
    OWNER to postgres;

-- Table: public.installed_software
-- DROP TABLE public.installed_software;

CREATE TABLE public.installed_software
(
    name text COLLATE pg_catalog."default" NOT NULL,
    version text COLLATE pg_catalog."default" NOT NULL,
    raw_version text COLLATE pg_catalog."default",
    architecture text COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default",
    vendor text COLLATE pg_catalog."default",
    publisher text COLLATE pg_catalog."default",
    cve_count int,
    sw_license text COLLATE pg_catalog."default",
    -- TODO: move this to adapter_device_installed_software, requires fixes in transfer
    path text COLLATE pg_catalog."default",
    CONSTRAINT installed_software_pkey PRIMARY KEY (version, name)
);

ALTER TABLE public.installed_software
    OWNER to postgres;

-- Table: public.network_interfaces

-- DROP TABLE public.network_interfaces;

CREATE TABLE public.network_interfaces
(
    device_id uuid NOT NULL,
    fetch_cycle int NOT NULL ,
    mac_addr macaddr,
    ip_addrs inet[],
    name text COLLATE pg_catalog."default",
    manufacturer text COLLATE pg_catalog."default",
    subnets cidr[],
    operational_status text COLLATE pg_catalog."default",
    admin_status text COLLATE pg_catalog."default",
    port_type text COLLATE pg_catalog."default",
    mtu text COLLATE pg_catalog."default",
    gateway inet,
    port smallint,
    CONSTRAINT device_mac UNIQUE (device_id, fetch_cycle, mac_addr)

) PARTITION BY LIST (fetch_cycle);

ALTER TABLE public.network_interfaces
    OWNER to postgres;

CREATE TABLE IF NOT EXISTS public.network_interfaces_vlan
(
    device_id uuid NOT NULL,
    fetch_cycle int NOT NULL ,
    tagId int,
    tagged boolean,
    mac_addr macaddr,
    name text,
    CONSTRAINT network_interface_vlan UNIQUE (device_id, fetch_cycle, mac_addr, name)

) PARTITION BY LIST (fetch_cycle);

ALTER TABLE public.network_interfaces_vlan
    OWNER to postgres;

-- Table: public.operating_systems

-- DROP TABLE public.operating_systems;

CREATE TABLE public.operating_systems
(
    id uuid,
    major int,
    minor int,
    type text COLLATE pg_catalog."default",
    architecture smallint,
    description text COLLATE pg_catalog."default",
    distribution text COLLATE pg_catalog."default",
    service_pack text COLLATE pg_catalog."default",
    kernel_version text COLLATE pg_catalog."default",
    code_name text COLLATE pg_catalog."default",
    build text COLLATE pg_catalog."default",
    raw_name text  COLLATE pg_catalog."default",

    CONSTRAINT operating_systems_pkey PRIMARY KEY (id),
    CONSTRAINT os_unique UNIQUE (type, architecture, distribution)
);


ALTER TABLE public.operating_systems
    OWNER to postgres;


-- Table: public.tags

-- DROP TABLE public.tags;

CREATE TABLE public.adapter_device_tags
(
    adapter_device_id uuid NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT adapter_devices_tags_pkey PRIMARY KEY (adapter_device_id, name)
);

ALTER TABLE public.adapter_device_tags
    OWNER to postgres;

-- Table: public.tags

-- DROP TABLE public.tags;

CREATE TABLE public.tags
(
    name text COLLATE pg_catalog."default" NOT NULL,
    level text COLLATE pg_catalog."default" NOT NULL,
    creator text COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT tags_pkey PRIMARY KEY (name)
);

ALTER TABLE public.tags
    OWNER to postgres;

-- Table: public.firewall_rules

-- DROP TABLE public.firewall_rules;

CREATE TABLE public.adapter_device_firewall_rules
(
    adapter_device_id uuid NOT NULL,
    fetch_cycle int NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT adapter_devices_firewall_rules_pkey PRIMARY KEY (adapter_device_id, fetch_cycle, name)
) PARTITION BY LIST (fetch_cycle);

ALTER TABLE public.adapter_device_firewall_rules
    OWNER to postgres;

-- Table: public.tags

-- DROP TABLE public.tags;

CREATE TABLE public.firewall_rules
(
    name text COLLATE pg_catalog."default" NOT NULL,
    type text COLLATE pg_catalog."default" NOT NULL,
    source text COLLATE pg_catalog."default" NOT NULL,
    target text COLLATE pg_catalog."default" NOT NULL,
    protocol text COLLATE pg_catalog."default" NOT NULL,
    direction text COLLATE pg_catalog."default" NOT NULL,
    src_port int,
    dst_port int,
    CONSTRAINT firewall_rules_pkey PRIMARY KEY (name)
);

ALTER TABLE public.firewall_rules
    OWNER to postgres;




-- Table: public.devices

-- DROP TABLE public.devices;

CREATE TABLE public.devices
(
    id uuid NOT NULL,
    fetch_cycle int NOT NULL,
    hostnames text[] COLLATE pg_catalog."default",
    adapter_names text[] COLLATE pg_catalog."default",
    adapter_count int NOT NULL,
    last_seen bigint,
    CONSTRAINT devices_pkey PRIMARY KEY (id, fetch_cycle)
) PARTITION BY LIST (fetch_cycle);

ALTER TABLE public.devices
    OWNER to postgres;



CREATE TABLE public.adapter_users
(
    id                      uuid NOT NULL,
    fetch_cycle             int NOT NULL,
    adapter_name            text COLLATE pg_catalog."default",
    adapter_id              text,
    user_id                 uuid,
    data                    jsonb,
    last_seen               bigint,
    fetch_time              bigint,


    display_name            text COLLATE pg_catalog."default",
    description             text COLLATE pg_catalog."default",
    domain                  text COLLATE pg_catalog."default",
    user_sid                text COLLATE pg_catalog."default",
    mail                    text COLLATE pg_catalog."default",


    admin                   bool default null,
    local                   bool default null,
    delegated_admin         bool default null,
    mfa_enforced            bool default null,
    mfa_enrolled            bool default null,
    suspended               bool default null,
    locked                  bool default null,
    disabled                bool default null,

    creation_date           bigint,
    last_logon              bigint,
    last_logoff             bigint,
    account_expires         bigint,
    last_bad_logon          bigint,
    last_password_change    bigint,
    logon_count             int,
    status                  text COLLATE pg_catalog."default",

    password_expiration_date bigint,
    password_expires         bool default null,
    password_required        bool default null,

    first_name               text COLLATE pg_catalog."default",
    last_name                text COLLATE pg_catalog."default",
    username                 text COLLATE pg_catalog."default",

    organizational_units     text[] COLLATE pg_catalog."default",
    groups                   text[] COLLATE pg_catalog."default",

    CONSTRAINT adapter_users_pkey PRIMARY KEY (id, fetch_cycle)
) PARTITION BY LIST (fetch_cycle);

ALTER TABLE public.adapter_users
    OWNER to postgres;


-- Table: public.users

-- DROP TABLE public.users;

CREATE TABLE public.users
(
    id uuid NOT NULL,
    fetch_cycle int NOT NULL,
    usernames text[] COLLATE pg_catalog."default",
    adapter_names text[] COLLATE pg_catalog."default",
    adapter_count int NOT NULL,
    last_seen bigint,
    CONSTRAINT users_pkey PRIMARY KEY (id, fetch_cycle)
) PARTITION BY LIST (fetch_cycle);

ALTER TABLE public.users
    OWNER to postgres;


CREATE TABLE public.lifecycle
(
    id serial,
    fetch_time bigint,
    end_time bigint,
    CONSTRAINT lifecycle_pkey PRIMARY KEY (id),
    UNIQUE (fetch_time)
);



ALTER TABLE public.lifecycle
    OWNER to postgres;

-- Create base partitions, these partitions are usually empty
CREATE TABLE adapter_devices_firewall_rules_cycle_0 PARTITION OF adapter_device_firewall_rules FOR VALUES IN (0);
CREATE TABLE adapter_devices_cycle_0 PARTITION OF adapter_devices FOR VALUES IN (0);
CREATE TABLE adapter_device_installed_software_cycle_0 PARTITION OF adapter_device_installed_software FOR VALUES IN (0);
CREATE TABLE network_interfaces_cycle_0 PARTITION OF network_interfaces FOR VALUES IN (0);
CREATE TABLE devices_cycle_0 PARTITION OF devices FOR VALUES IN (0);
CREATE TABLE adapter_users_cycle_0 PARTITION OF adapter_users FOR VALUES IN (0);
CREATE TABLE users_cycle_0 PARTITION OF users FOR VALUES IN (0);


-- Common UNKNOWN OS
INSERT INTO operating_systems (id, major, minor, type, architecture, description, distribution, service_pack,
                               kernel_version, code_name, build, raw_name)
                               VALUES ('41d22eb3-f27e-471b-4341-770e585fa787', 0, 0, 'Unknown', 0, '', '', '', '',
                                       '', '', '')