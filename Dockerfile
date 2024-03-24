# build stage
FROM python:3.8-alpine AS builder

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

# copy files
COPY pyproject.toml pdm.lock README.md /lyrics-maid/
COPY src/ /lyrics-maid/src

# install dependencies and lyrics-maid into the local packages directory
WORKDIR /lyrics-maid
RUN mkdir __pypackages__ && pdm sync -v --prod --no-editable


# run stage
FROM python:3.8-alpine
MAINTAINER Rongyi Chen <kenchenrong@gmail.com>

# retrieve packages from build stage
ENV PYTHONPATH=/lyrics-maid/pkgs
COPY --from=builder /lyrics-maid/__pypackages__/3.8/lib /lyrics-maid/pkgs

# retrieve executables
COPY --from=builder /lyrics-maid/__pypackages__/3.8/bin/* /bin/

RUN mkdir /config
WORKDIR /config

# set command/entrypoint, adapt to fit your needs
ENTRYPOINT ["lyrics-maid"]
