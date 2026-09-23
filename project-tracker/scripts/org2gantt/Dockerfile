FROM ruby:3.3-slim
# Browsers outside /root and a writable HOME, so `docker run --user` works.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright HOME=/tmp
# Same pins as install-deps: Gemfile, requirements.txt.
COPY Gemfile requirements.txt /opt/org2gantt/
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip \
 && gem install --no-document taskjuggler \
      -v "$(sed -n 's/^gem "taskjuggler", "\(.*\)"$/\1/p' /opt/org2gantt/Gemfile)" \
 && pip3 install --break-system-packages -r /opt/org2gantt/requirements.txt \
 && python3 -m playwright install --with-deps --only-shell chromium \
 && rm -rf /var/lib/apt/lists/*
COPY org2gantt orgtj.py /opt/org2gantt/
RUN chmod +x /opt/org2gantt/org2gantt && ln -s /opt/org2gantt/org2gantt /usr/local/bin/org2gantt
WORKDIR /work
ENTRYPOINT ["org2gantt"]
