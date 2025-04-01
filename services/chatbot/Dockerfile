FROM public.ecr.aws/lambda/python:3.10

# Copy function files to Lambda's working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Install Poetry and dependencies
RUN pip install poetry

COPY . .


RUN poetry config virtualenvs.create false \
  && poetry install --no-root

# Lambda will look for `handler` inside app.main
CMD ["app.main.handler"] 