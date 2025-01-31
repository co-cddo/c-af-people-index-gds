FROM public.ecr.aws/docker/library/python:3.11.4-slim AS installer-image

# Install the function's dependencies using file requirements.txt
# from your project folder.

ARG local_config="false"
RUN if [[ "$local_config" = "true" ]] ; then yum install -y tar gzip; else echo "tar wont be installed" ;fi

#WORKDIR /workspace
#ADD . /workspace

RUN apt-get update && apt-get install -y \
    gcc

RUN mkdir code
COPY ./app /code

RUN pip3 install -r /code/requirements.txt

# Expose the port on which Gradio will run
EXPOSE 7860

# Command to run the Gradio app
ENTRYPOINT ["python", "./app/people_finder_chromadb.py"]
