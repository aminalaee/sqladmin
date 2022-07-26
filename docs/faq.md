### How to deploy to production with HTTPS enabled?

This is not really related to `SQLAdmin` but in case you are deploying in a production
environment you will enable HTTPS with a reverse proxy like Nginx or Kubernetes Ingress.

If you are deploying the application with `Uvicorn` you can follow the docs for
[running behind nginx](https://www.uvicorn.org/deployment/#running-behind-nginx) and all you
probably need is to start `Uvicorn` with `--forwarded-allow-ips='*'` and `--proxy-headers` to
pass the correct HTTP headers.
