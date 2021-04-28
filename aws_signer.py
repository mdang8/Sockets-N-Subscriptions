import datetime, hashlib, hmac

class AwsSigner:
    def __init__(self, aws_access_key, aws_secret_key):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key

    @staticmethod
    def sign(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    @staticmethod
    def create_canonical_request(method, host, amz_date, signed_headers, query_params, payload=''):
        """
        From AWS docs (https://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html):
            CanonicalRequest =
                HTTPRequestMethod + '\n' +
                CanonicalURI + '\n' +
                CanonicalQueryString + '\n' +
                CanonicalHeaders + '\n' +
                SignedHeaders + '\n' +
                HexEncode(Hash(RequestPayload))
        """
        canonical_uri = '/'
        canonical_querystring = f'{query_params}'
        canonical_headers = f'host:{host}\nx-amz-date:{amz_date}\n'
        payload_hash = hashlib.sha256((payload).encode('utf-8')).hexdigest()
        canonical_req = f'{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
        return canonical_req

    @staticmethod
    def create_signed_str(algorithm, amz_date, credential_scope, canonical_req_hash):
        """
        From AWS docs (https://docs.aws.amazon.com/general/latest/gr/sigv4-create-string-to-sign.html):
            StringToSign =
                Algorithm + \n +
                RequestDateTime + \n +
                CredentialScope + \n +
                HashedCanonicalRequest
        """
        signed_str = f'{algorithm}\n{amz_date}\n{credential_scope}\n{canonical_req_hash}'
        return signed_str

    def get_signature_key(self, k_secret, date_stamp, region, service):
        """
        From AWS docs (https://docs.aws.amazon.com/general/latest/gr/sigv4-calculate-signature.html):
            Pseudocode for deriving signing key:
                kSecret = your secret access key
                kDate = HMAC("AWS4" + kSecret, Date)
                kRegion = HMAC(kDate, Region)
                kService = HMAC(kRegion, Service)
                kSigning = HMAC(kService, "aws4_request")
        """
        k_date = self.sign(('AWS4' + k_secret).encode('utf-8'), date_stamp)
        k_region = self.sign(k_date, region)
        k_service = self.sign(k_region, service)
        k_signing = self.sign(k_service, 'aws4_request')
        return k_signing
    
    def generate_signed_req_headers(self, method, host, region, service, query_params):
        """
        From AWS docs (https://docs.aws.amazon.com/general/latest/gr/sigv4-add-signature-to-request.html):
            Pseudocode for Authorization header:
                Authorization: algorithm Credential=access key ID/credential scope, SignedHeaders=SignedHeaders, Signature=signature
        """
        current_time = datetime.datetime.utcnow()
        amz_date = current_time.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = current_time.strftime('%Y%m%d')

        signed_headers = 'host;x-amz-date'
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'

        # Task 1: Create a canonical request for Signature Version 4
        canonical_req = self.create_canonical_request(method, host, amz_date, signed_headers, query_params)
        canonical_req_hash = hashlib.sha256(canonical_req.encode('utf-8')).hexdigest()

        # Task 2: Create a string to sign for Signature Version 4
        signed_str = self.create_signed_str(algorithm, amz_date, credential_scope, canonical_req_hash)
        signing_key = self.get_signature_key(self.aws_secret_key, date_stamp, region, service)

        # Task 3: Calculate the signature for AWS Signature Version 4
        signature = hmac.new(signing_key, (signed_str).encode('utf-8'), hashlib.sha256).hexdigest()

        # Task 4: Add the signature to the HTTP request
        auth_header = f'{algorithm} Credential={self.aws_access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
        
        return (auth_header, amz_date)
