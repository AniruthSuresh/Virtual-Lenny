FROM public.ecr.aws/lambda/python:3.11

RUN yum install -y gcc gcc-c++ make && yum clean all

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the mxbai model into the image during build
RUN python -c "from sentence_transformers import SentenceTransformer; \
    model = SentenceTransformer('mixedbread-ai/mxbai-embed-large-v1'); \
    model.save('/var/task/mxbai_model')"

COPY handler.py .
CMD ["handler.lambda_handler"]