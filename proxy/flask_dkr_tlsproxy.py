# FROM
# https://gist.github.com/gear11/8006132

"""
A simple proxy server to proxy docker API with TLS auth. Usage:
http://hostname:port/p/(URL to be proxied, minus protocol)
Supply header Docker-Credentials-Zipfile with zipped docker credentials directory 
(output directory of docker-machine)

TODO: verify server TLS
"""
from flask import Flask, render_template, request, abort, Response, redirect
import requests
import logging

import tarfile,base64
from io import BytesIO

try:
  from cStringIO import StringIO
except:
  from StringIO import StringIO
import zipfile

import ssl, tempfile


app = Flask(__name__.split('.')[0])
logging.basicConfig(level=logging.INFO)
APPROVED_HOSTS = set(["google.com", "www.google.com", "yahoo.com"])
CHUNK_SIZE = 1024
LOG = logging.getLogger("main.py")


@app.route('/<path:url>')
def root(url):
    LOG.info("Root route, path: %s", url)
    # If referred from a proxy request, then redirect to a URL with the proxy prefix.
    # This allows server-relative and protocol-relative URLs to work.
    proxy_ref = proxy_ref_info(request)
    if proxy_ref:
        redirect_url = "/p/%s/%s%s" % (proxy_ref[0], url, ("?" + request.query_string if request.query_string else ""))
        LOG.info("Redirecting referred URL to: %s", redirect_url)
        return redirect(redirect_url)
    # Otherwise, default behavior
    return render_template('hello.html', name=url,request=request)


@app.route('/p/<path:url>', methods=['GET', 'POST', 'DELETE'])
def proxy(url):
    """Fetches the specified URL and streams it out to the client.
    If the request was referred by the proxy itself (e.g. this is an image fetch for
    a previously proxied HTML page), then the original Referer is passed."""
    
    # TODO HERE: protect this from exposing of debug info / header name
    
    dkr_cred_zip = base64.b64decode(request.headers.get("Docker-Credentials-Zipfile"))
    certs = extract_certs_zip(dkr_cred_zip)
    
    r = get_source_rsp(url, certs, request.method, request.data)
    LOG.info("Got %s response from %s",r.status_code, url)
    
    headers = dict(r.headers)
    def generate():
        for chunk in r.iter_content(CHUNK_SIZE):
            yield chunk
    return Response(generate(), headers = headers)


def get_source_rsp(url, certs, method, payload):
        # TODO HERE: implement get or post!
        url = 'https://%s' % url
        LOG.info("Fetching %s", url)
        # Ensure the URL is approved, else abort
        if not is_approved(url):
            LOG.warn("URL is not approved: %s", url)
            abort(403)
        # Pass original Referer for subsequent resource requests
        proxy_ref = proxy_ref_info(request)
        #headers = { "Referer" : "http://%s/%s" % (proxy_ref[0], proxy_ref[1])} if proxy_ref else {}
        headers = { "Content-Type": "application/json" }
        # Fetch the URL, and stream it back
        LOG.info("Fetching with headers: %s, %s", url, headers)
        LOG.info("Sending payload data %s", payload)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        # set other SSLContext options you might need
        #response = urllib2.urlopen(url, context=ctx)
        
        # https://stackoverflow.com/a/13464600
        # https://stackoverflow.com/questions/893333/multiple-variables-in-python-with-statement
        with tempfile.NamedTemporaryFile() as cert, tempfile.NamedTemporaryFile() as key:
        
            cert.write(certs["cert.pem"])
            cert.flush()
            
            key.write(certs["key.pem"])
            key.flush()
            
            print "Running with certs: ", cert.name, key.name
        
            # https://stackoverflow.com/questions/30598950/python-requests-send-certificate-as-string
            # http://docs.python-requests.org/en/master/user/advanced/?highlight=ssl
            
            # XXX TODO HERE: do cert verification!
            if method=="POST":
                runmethod = requests.post
            elif method=="GET":
                runmethod = requests.get
            elif method=="DELETE":
                runmethod = requests.delete
            else:
                abort(400)
            res = runmethod(url, stream=True , verify=False, params = request.args, headers=headers, cert=(cert.name, key.name), data=payload)
        
        return res


def is_approved(url):
    """Indicates whether the given URL is allowed to be fetched.  This
    prevents the server from becoming an open proxy"""
    host = split_url(url)[1]
    # WARNING: always approved
    return True
    #return host in APPROVED_HOSTS


def split_url(url):
    """Splits the given URL into a tuple of (protocol, host, uri)"""
    proto, rest = url.split(':', 1)
    rest = rest[2:].split('/', 1)
    host, uri = (rest[0], rest[1]) if len(rest) == 2 else (rest[0], "")
    return (proto, host, uri)


def proxy_ref_info(request):
    """Parses out Referer info indicating the request is from a previously proxied page.
    For example, if:
        Referer: http://localhost:8080/p/google.com/search?q=foo
    then the result is:
        ("google.com", "search?q=foo")
    """
    ref = request.headers.get('referer')
    if ref:
        _, _, uri = split_url(ref)
        if uri.find("/") < 0:
            return None
        first, rest = uri.split("/", 1)
        if first in "pd":
            parts = rest.split("/", 1)
            r = (parts[0], parts[1]) if len(parts) == 2 else (parts[0], "")
            LOG.info("Referred by proxy host, uri: %s, %s", r[0], r[1])
            return r
    return None
    


def extract_certs(filecontent):
    out = BytesIO()
    out.write(base64.b64decode(filecontent))
    tar = tarfile.open(mode = "w:gz", fileobj = out)
    data = 'lala'.encode('utf-8')
    file = BytesIO(data)
    info = tarfile.TarInfo(name="1.txt")
    info.size = len(data)
    tar.addfile(tarinfo=info, fileobj=file)
    tar.close()
    # response = HttpResponse(out.getvalue(), content_type='application/tgz')
    # response['Content-Disposition'] = 'attachment; filename=myfile.tgz'
    # return response
    
def extract_certs_zip(data):
    fp = StringIO(data)
    zfp = zipfile.ZipFile(fp, "r")
    zinfo = zfp.namelist()
    s_certs = {}
    for f in zinfo:
        s_certs[f] = zfp.open(f).read()
    return s_certs
    
    
# http://flask.pocoo.org/docs/0.12/quickstart/
# RUNNING:
# export FLASK_APP=./flask_tlsproxy.py; flask run
# NEW PYTHON RUN
# export FLASK_APP=./flask_tlsproxy.py; /usr/bin/python2.7 -m flask run --host=0.0.0.0 --port=8080