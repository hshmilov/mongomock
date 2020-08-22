from pathlib import Path

CORTEX_PATH = Path(__file__).resolve().parent.parent.parent
NGINX_CONF_PATH = CORTEX_PATH / 'axonius-libs/src/config/'
NGINX_API_CONF_FILE_PATH = NGINX_CONF_PATH / 'nginx_api.conf'
NGINX_CONF_FILE_PATH = NGINX_CONF_PATH / 'nginx.conf'

NGINX_API_ADDITION = 'access_log /home/axonius/logs/nginx-body.log log_req_resp;'
CHANGE_HTTP_AFTER_THIS_LINE = 'client_max_body_size 1000M;'
HTTP_ADDITION = '''    log_format log_req_resp '$remote_addr - $remote_user [$time_local] '
        '"$request" $status $body_bytes_sent '
        '"$http_referer" "$http_user_agent" $request_time req_body:"$request_body" resp_body:"$resp_body"';
'''
CHANGE_SERVER_AFTER_THIS_LINE = 'include /usr/local/openresty/nginx/conf/nginx_generic.conf;'
SERVER_ADDITION = '''        lua_need_request_body on;

        set $resp_body "";
        body_filter_by_lua '
            local resp_body = string.sub(ngx.arg[1], 1, 1000)
            ngx.ctx.buffered = (ngx.ctx.buffered or "") .. resp_body
            if ngx.arg[2] then
                ngx.var.resp_body = ngx.ctx.buffered
            end
        ';
'''


def add_lines_to_nginx_configs():
    # Appending NGINX_API_ADDITION to the end of the nginx_api.conf
    with NGINX_API_CONF_FILE_PATH.open('a') as nginx_api_conf_file:
        nginx_api_conf_file.write('\n' + NGINX_API_ADDITION)

    # Appending to nginx.conf

    with NGINX_CONF_FILE_PATH.open() as f:
        lines = f.readlines()

    new_config_file_lines = []
    for line in lines:
        new_config_file_lines.append(line)
        if CHANGE_HTTP_AFTER_THIS_LINE in line:
            new_config_file_lines.extend(HTTP_ADDITION.splitlines(True))
        elif CHANGE_SERVER_AFTER_THIS_LINE in line:
            new_config_file_lines.extend(SERVER_ADDITION.splitlines(True))
    NGINX_CONF_FILE_PATH.write_text(''.join(new_config_file_lines))


if __name__ == '__main__':
    add_lines_to_nginx_configs()
