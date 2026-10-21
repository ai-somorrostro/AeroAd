# Node-RED con el nodo contrib de InfluxDB preinstalado.
FROM nodered/node-red:4.0.2

USER root
COPY package.json /data/package.json
RUN npm install --no-audit --no-fund --prefix /data --omit=dev \
 && chown -R node-red:node-red /data
# El flow de prueba queda horneado en la imagen; un volumen con nombre nuevo
# lo hereda al crearse. Para renovarlo: rebuild + recrear el volumen.
COPY --chown=node-red:node-red flows.json /data/flows.json
# Entry point propio: exporta el token de InfluxDB desde el volumen compartido
# (influx-tokens-init) antes de arrancar, y delega en el entrypoint oficial.
COPY --chmod=0755 aeroadd-entrypoint.sh /usr/src/node-red/aeroadd-entrypoint.sh
ENTRYPOINT ["/usr/src/node-red/aeroadd-entrypoint.sh"]

USER node-red
