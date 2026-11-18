# EcoCity Guardian — módulo IoT

O projeto usa uma simulação ESP32 DevKit v1 com sensor ultrassônico HC-SR04 e LED de alerta.

## Executar no Wokwi

1. Abra o [Wokwi](https://wokwi.com/) e crie um projeto ESP32.
2. Importe `sketch.ino`, `diagram.json` e `libraries.txt`.
3. Inicie a API FastAPI seguindo o arquivo `../GUIA_EXECUCAO.md`.
4. Configure no `sketch.ino` o endereço acessível da API (`serverUrl`) e a mesma chave que está em `SENSOR_API_KEY` no arquivo `ia/.env` (`sensorApiKey`).
5. Para uma placa física, use o IP local do computador e execute a API com `--host 0.0.0.0`. Para Wokwi na nuvem, use um túnel HTTPS ou endpoint público protegido; `localhost` não será o seu computador.

O sketch envia uma requisição JSON com `sensor_id`, `localizacao`, `descricao` e `nivel_sensor_agua_cm` para `POST /api/v1/telemetria`, usando o cabeçalho `X-Sensor-Token`. O servidor classifica a leitura e cria um registro que aparece no Painel do Gestor.

O envio ocorre quando o nível calculado supera 50 cm. Se a condição persistir, serão criados novos registros a cada ciclo de 10 segundos. Antes de uma operação contínua, adicione um intervalo de cooldown/agrupamento e configure uma chave de sensor forte.

> A conexão física/Wokwi depende da rede e do endereço configurados no ambiente e ainda precisa ser validada no dispositivo. As ocorrências de telemetria não aparecem automaticamente como novos pontos no mapa até que latitude/longitude sejam adicionadas ao contrato da API.
