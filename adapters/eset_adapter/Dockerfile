FROM axonius/axonius-libs

# Copying needed shared library /usr/bin for debugging and /usr/local/bin for prod.
COPY ./ERAApi/Network.so /usr/bin/
COPY ./ERAApi/Network.so /usr/local/bin/

# Copying the eset_connect.cpp
COPY ./ERAApi/* /home/axonius/bin/

# Compiling the eset_connect.cpp
RUN cd /home/axonius/bin && make