FROM public.ecr.aws/lambda/python:3.10

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}


# Install Poetry and dependencies
RUN pip install poetry

COPY . .

RUN poetry config virtualenvs.create false \
  && poetry install --no-root

# Entrypoint for AWS Lambda
CMD ["main.handler"]