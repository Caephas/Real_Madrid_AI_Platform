FROM public.ecr.aws/lambda/python:3.10

WORKDIR ${LAMBDA_TASK_ROOT}

# Poetry & dependencies
RUN pip install poetry

COPY . .

RUN poetry config virtualenvs.create false \
  && poetry install --no-root

CMD ["main.handler"]