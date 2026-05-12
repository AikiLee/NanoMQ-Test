# 操作手册

```shell
CERT_DIR=/tmp/nanomq-cert-materials
rm -rf "$CERT_DIR"
mkdir -p "$CERT_DIR"/{root,device,verify,expired,non-ca}
```

## 1. 合法私有 Root CA

这是你自己的信任根。它必须是自签名，并且扩展里要有 CA:TRUE 和 keyCertSign。

```shell
openssl genrsa -out "$CERT_DIR/root/root_ca.key" 4096

openssl req -x509 -new -nodes \
  -key "$CERT_DIR/root/root_ca.key" \
  -sha256 -days 3650 \
  -out "$CERT_DIR/root/root_ca.pem" \
  -subj "/CN=NanoMQ Study Root CA" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:1" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "subjectKeyIdentifier=hash"
```

产物：

root/root_ca.key   # Root CA 私钥，必须保护好
root/root_ca.pem   # Root CA 证书，客户端信任它

## 2. 合法设备证书，由该 Root CA 签发

如果这是设备接入 MQTT mTLS 用的证书，建议使用 extendedKeyUsage=clientAuth。

```shell
openssl genrsa -out "$CERT_DIR/device/device.key" 2048

openssl req -new \
  -key "$CERT_DIR/device/device.key" \
  -out "$CERT_DIR/device/device.csr" \
  -subj "/CN=device-001"

cat > "$CERT_DIR/device/device.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
subjectAltName=URI:urn:nanomq-study:device:device-001
authorityKeyIdentifier=keyid,issuer
EOF

openssl x509 -req \
  -in "$CERT_DIR/device/device.csr" \
  -CA "$CERT_DIR/root/root_ca.pem" \
  -CAkey "$CERT_DIR/root/root_ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/device/device.pem" \
  -days 365 \
  -sha256 \
  -extfile "$CERT_DIR/device/device.ext"
```

产物：

device/device.key
device/device.pem
验证：

openssl verify \
  -purpose sslclient \
  -CAfile "$CERT_DIR/root/root_ca.pem" \
  "$CERT_DIR/device/device.pem"
预期：

device.pem: OK

## 3. 验证证书，由 Root CA 私钥签发，CN 填平台验证码

这个证书一般不是给 TLS 长期通信用，而是给平台做“你确实持有 Root CA 私钥”的证明。所以 CN 可以填平台验证码。

示例验证码：

PLATFORM_CODE=platform-verify-abc123
生成验证证书：

```shell
openssl genrsa -out "$CERT_DIR/verify/verify.key" 2048

openssl req -new \
  -key "$CERT_DIR/verify/verify.key" \
  -out "$CERT_DIR/verify/verify.csr" \
  -subj "/CN=$PLATFORM_CODE"

cat > "$CERT_DIR/verify/verify.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
authorityKeyIdentifier=keyid,issuer
EOF

openssl x509 -req \
  -in "$CERT_DIR/verify/verify.csr" \
  -CA "$CERT_DIR/root/root_ca.pem" \
  -CAkey "$CERT_DIR/root/root_ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/verify/verify.pem" \
  -days 30 \
  -sha256 \
  -extfile "$CERT_DIR/verify/verify.ext"
```

openssl verify 默认不把非自签名的 intermediate 当作链条终点。

检查 CN：

openssl x509 -in "$CERT_DIR/verify/verify.pem" -noout -subject
预期能看到：

subject=CN=platform-verify-abc123

## 4. 过期 CA、过期设备证书

OpenSSL 不太适合直接用 -days -1。更稳的方式是用固定 -startdate / -enddate，但 openssl x509 -req 对版本支持有差异。测试里可以用 -days 0 准备“立即过期/极短有效期”证书，或者后续用 Python cryptography 精准生成过期证书。

如果先用 OpenSSL 简化准备：

```shell
openssl req -x509 -new -nodes \
  -key "$CERT_DIR/root/root_ca.key" \
  -sha256 -days 0 \
  -out "$CERT_DIR/expired/expired_ca.pem" \
  -subj "/CN=Expired Study Root CA" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:1" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
```

过期设备证书同理：

```shell
openssl genrsa -out "$CERT_DIR/expired/expired_device.key" 2048

openssl req -new \
  -key "$CERT_DIR/expired/expired_device.key" \
  -out "$CERT_DIR/expired/expired_device.csr" \
  -subj "/CN=expired-device-001"

cat > "$CERT_DIR/expired/expired_device.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
EOF

openssl x509 -req \
  -in "$CERT_DIR/expired/expired_device.csr" \
  -CA "$CERT_DIR/root/root_ca.pem" \
  -CAkey "$CERT_DIR/root/root_ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/expired/expired_device.pem" \
  -days 0 \
  -sha256 \
  -extfile "$CERT_DIR/expired/expired_device.ext"
```

验证时预期失败，通常会看到 certificate has expired。

## 5. 非 CA 证书冒充 CA

这个 case 的意思是：生成一个 CA:FALSE 的证书，然后尝试用它签发设备证书。验证链时应该失败。

先生成“假 CA”：

```shell
openssl genrsa -out "$CERT_DIR/non-ca/fake_ca.key" 2048

openssl req -x509 -new -nodes \
  -key "$CERT_DIR/non-ca/fake_ca.key" \
  -sha256 -days 365 \
  -out "$CERT_DIR/non-ca/fake_ca.pem" \
  -subj "/CN=Fake Non CA" \
  -addext "basicConstraints=critical,CA:FALSE" \
  -addext "keyUsage=critical,digitalSignature,keyEncipherment"
```

再用它签一个设备证书：

BASE=/Users/lee/Test/ca_cert/tmp/nanomq-cert-materials
DEVICE_ID=69fecdb1c9429d337f46f569_cert_intermediate_device01_0_0_2026051108

mkdir -p "$BASE/device-by-intermediate"



```shell
openssl genrsa -out "$CERT_DIR/non-ca/fake_signed_device.key" 2048

openssl req -new \
  -key "$CERT_DIR/non-ca/fake_signed_device.key" \
  -out "$CERT_DIR/non-ca/fake_signed_device.csr" \
  -subj "/CN=fake-signed-device"

cat > "$CERT_DIR/non-ca/fake_signed_device.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=clientAuth
EOF

openssl x509 -req \
  -in "$CERT_DIR/non-ca/fake_signed_device.csr" \
  -CA "$CERT_DIR/non-ca/fake_ca.pem" \
  -CAkey "$CERT_DIR/non-ca/fake_ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/non-ca/fake_signed_device.pem" \
  -days 365 \
  -sha256 \
  -extfile "$CERT_DIR/non-ca/fake_signed_device.ext"
```

验证：

openssl verify \
  -purpose sslclient \
  -CAfile "$CERT_DIR/non-ca/fake_ca.pem" \
  "$CERT_DIR/non-ca/fake_signed_device.pem"
预期失败，核心原因是 issuer 不是合法 CA，常见会出现：

invalid CA certificate
或类似 key usage does not include certificate signing。

这 5 类材料准备好后，后续 pytest case 可以按这些目录直接读取证书，分别覆盖：合法链、验证码证书、过期证书、非 CA 冒充 CA。

## 6. NanoMQ 本地 mTLS 自动化闭环

当前项目新增了一个本地 NanoMQ mTLS 准备脚本。它不会连接华为云，也不会提交任何证书私钥到仓库。

生成临时材料：

```shell
./venv/bin/python scripts/prepare_nanomq_mtls.py
```

生成目录：

```text
.tmp/nanomq-mtls/
```

主要产物：

```text
root/root_ca.pem
intermediate/intermediate_ca.pem
server/server_chain.pem
server/server.key
device/device_chain.pem
device/device.key
wrong-device/wrong_device.pem
wrong-device/wrong_device.key
nanomq-mtls.conf
manifest.json
```

证书关系：

```text
Root CA
  -> Intermediate CA
    -> server certificate
    -> device certificate

Wrong Root CA
  -> wrong device certificate
```

NanoMQ 配置使用：

```text
certfile = server_chain.pem
keyfile = server.key
cacertfile = root_ca.pem
verify_peer = true
fail_if_no_peer_cert = true
```

启动 NanoMQ：

```shell
nanomq start --conf .tmp/nanomq-mtls/nanomq-mtls.conf
```

运行 mTLS E2E：

```shell
RUN_NANOMQ_MTLS_E2E=1 ./venv/bin/pytest tests/test_e2e/test_nanomq_mtls.py -v
```

自动化覆盖：

```text
合法设备证书连接成功
合法设备证书可以订阅和发布消息
不提供客户端证书会被拒绝
错误 CA 签发的设备证书会被拒绝
缺少 intermediate 链的设备证书会被拒绝
```
