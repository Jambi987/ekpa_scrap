"""Useful error summaries that never echo request headers, bodies or URLs."""
import re


def request_error_hint(exc):
    message = str(exc).lower()
    if any(word in message for word in ('self_signed_cert', 'self-signed certificate', 'self signed certificate', 'unable_to_verify_leaf_signature', 'unable to verify the first certificate', 'unable to get local issuer certificate', 'err_cert_authority_invalid')):
        return ('TLS certificate trust failed. On Windows set NODE_USE_SYSTEM_CA=1 before running Python. '
                'If needed, set NODE_EXTRA_CA_CERTS to your IT-provided PEM root certificate. '
                'Certificate verification remains enabled.')
    if 'timeout' in message or 'timeout' in type(exc).__name__.lower():
        return 'The request timed out. Check the site, network, VPN and proxy connection.'
    if 'err_aborted' in message or 'interrupted by another navigation' in message:
        return 'Page navigation was interrupted by another redirect. Retry after login finishes.'
    code = re.search(r'net::(ERR_[A-Z0-9_]+)', str(exc))
    if code:
        return f'Browser network error {code[1]}. Check the network, VPN and proxy connection.'
    if 'enotfound' in message or 'eai_again' in message:
        return 'The site hostname could not be resolved. Check DNS, VPN and proxy settings.'
    return f'Request failed ({type(exc).__name__}). Raw request details were omitted.'
