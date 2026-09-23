FROM ruby:3.3-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip \
 && gem install taskjuggler --no-document \
 && pip3 install --break-system-packages playwright \
 && python3 -m playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*
COPY org2gantt orgtj.py /opt/org2gantt/
RUN chmod +x /opt/org2gantt/org2gantt && ln -s /opt/org2gantt/org2gantt /usr/local/bin/org2gantt
WORKDIR /work
ENTRYPOINT ["org2gantt"]
