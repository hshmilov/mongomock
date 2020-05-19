
CREATE INDEX adapter_devices_adapter_id_idx ON public.adapter_devices USING btree (adapter_id);

CREATE INDEX adapter_devices_device_id_idx ON public.adapter_devices USING btree (device_id);

CREATE INDEX hostname_trgm_idx ON public.adapter_devices USING gin (hostname COLLATE pg_catalog."default" gin_trgm_ops);
CREATE INDEX last_used_users_trgm_idx ON public.adapter_devices USING gin (arrayToText(last_used_users) COLLATE pg_catalog."default" gin_trgm_ops) WHERE last_used_users is not null;
CREATE INDEX name_trgm_idx ON public.adapter_devices USING gin (name COLLATE pg_catalog."default" gin_trgm_ops);

CREATE INDEX adapter_users_users_id_idx ON public.adapter_users USING btree (user_id);

CREATE INDEX username_trgm_idx ON public.adapter_users USING gin (username COLLATE pg_catalog."default" gin_trgm_ops);
CREATE INDEX mail_trgm_idx ON public.adapter_users USING gin (mail COLLATE pg_catalog."default" gin_trgm_ops);
CREATE INDEX first_name_trgm_idx ON public.adapter_users USING gin (mail COLLATE pg_catalog."default" gin_trgm_ops);
CREATE INDEX last_name_trgm_idx ON public.adapter_users USING gin (mail COLLATE pg_catalog."default" gin_trgm_ops);

CREATE INDEX devices_adapter_count_idx ON public.devices (adapter_count DESC);

CREATE INDEX users_adapter_count_idx ON public.users (adapter_count DESC);

CREATE INDEX lifecycle_fetch_time_idx ON public.lifecycle USING btree (fetch_time DESC);


CREATE INDEX os_type_trgm_idx ON public.adapter_users USING gin (mail COLLATE pg_catalog."default" gin_trgm_ops);

CREATE INDEX adapter_devices_last_seen_idx ON public.adapter_devices (last_seen DESC);

CREATE INDEX adapter_device_os_id_idx  ON public.adapter_devices using brin (os_id);

CREATE INDEX adapter_devices_adapter_name_idx ON public.adapter_devices  using brin (adapter_name);
CREATE INDEX user_devices_adapter_name_idx ON public.adapter_users  using brin (adapter_name);

