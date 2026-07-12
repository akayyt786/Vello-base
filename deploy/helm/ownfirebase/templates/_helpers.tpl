{{/*
Standard name/label helpers (helm create boilerplate pattern).
*/}}

{{- define "ownfirebase.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ownfirebase.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "ownfirebase.labels" -}}
helm.sh/chart: {{ include "ownfirebase.chart" . }}
{{ include "ownfirebase.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "ownfirebase.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ownfirebase.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* Per-component labels: `component` is e.g. "web", "websocket", "postgres" */}}
{{- define "ownfirebase.componentLabels" -}}
{{ include "ownfirebase.labels" .context }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "ownfirebase.componentSelectorLabels" -}}
{{ include "ownfirebase.selectorLabels" .context }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "ownfirebase.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "ownfirebase.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Resolved datastore connection settings — single place that implements the
postgresql.enabled / redis.enabled / minio.enabled toggles described in the
task (flip to false + point at an external managed service via values).
*/}}

{{- define "ownfirebase.databaseHost" -}}
{{- if .Values.postgresql.enabled -}}
{{- printf "%s-postgres" (include "ownfirebase.fullname" .) -}}
{{- else -}}
{{- .Values.externalDatabase.host -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.databasePort" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.service.port | toString -}}
{{- else -}}
{{- .Values.externalDatabase.port | toString -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.databaseName" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.database -}}
{{- else -}}
{{- .Values.externalDatabase.database -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.databaseUser" -}}
{{- if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.username -}}
{{- else -}}
{{- .Values.externalDatabase.username -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.databasePassword" -}}
{{- if .Values.secrets.databasePassword -}}
{{- .Values.secrets.databasePassword -}}
{{- else if .Values.postgresql.enabled -}}
{{- .Values.postgresql.auth.password -}}
{{- else -}}
{{- required "secrets.databasePassword is required when postgresql.enabled=false" .Values.secrets.databasePassword -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.redisUrl" -}}
{{- if .Values.redis.enabled -}}
{{- printf "redis://%s-redis:%v/0" (include "ownfirebase.fullname" .) .Values.redis.service.port -}}
{{- else -}}
{{- required "externalRedis.url is required when redis.enabled=false" .Values.externalRedis.url -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.s3Endpoint" -}}
{{- if .Values.minio.enabled -}}
{{- printf "http://%s-minio:%v" (include "ownfirebase.fullname" .) .Values.minio.service.apiPort -}}
{{- else -}}
{{- .Values.config.awsS3EndpointUrl -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.awsAccessKeyId" -}}
{{- if .Values.secrets.awsAccessKeyId -}}
{{- .Values.secrets.awsAccessKeyId -}}
{{- else if .Values.minio.enabled -}}
{{- .Values.minio.auth.rootUser -}}
{{- else -}}
{{- required "secrets.awsAccessKeyId is required when minio.enabled=false" .Values.secrets.awsAccessKeyId -}}
{{- end -}}
{{- end -}}

{{- define "ownfirebase.awsSecretAccessKey" -}}
{{- if .Values.secrets.awsSecretAccessKey -}}
{{- .Values.secrets.awsSecretAccessKey -}}
{{- else if .Values.minio.enabled -}}
{{- .Values.minio.auth.rootPassword -}}
{{- else -}}
{{- required "secrets.awsSecretAccessKey is required when minio.enabled=false" .Values.secrets.awsSecretAccessKey -}}
{{- end -}}
{{- end -}}

{{/*
Shared envFrom block (ConfigMap + Secret) used by every Django/Celery/
push-worker container so the ~45-key env surface only needs to be defined
once, in configmap.yaml/secret.yaml.
*/}}
{{- define "ownfirebase.envFrom" -}}
envFrom:
  - configMapRef:
      name: {{ include "ownfirebase.fullname" . }}-config
  - secretRef:
      name: {{ include "ownfirebase.fullname" . }}-secrets
{{- end -}}

{{/*
initContainers that block until bundled Postgres/Redis are actually
accepting connections — not just "created". Skips whichever check isn't
relevant (external datastore, or that datastore not yet enabled) since
there's nothing this chart manages to wait on in that case.
*/}}
{{- define "ownfirebase.waitForDeps" -}}
{{- if .Values.postgresql.enabled }}
- name: wait-for-postgres
  image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  command:
    - bash
    - -c
    - |
      until pg_isready -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" >/dev/null 2>&1; do
        echo "waiting for postgres at $DATABASE_HOST:$DATABASE_PORT..."
        sleep 2
      done
      echo "postgres is ready"
  envFrom:
    - configMapRef:
        name: {{ include "ownfirebase.fullname" . }}-config
{{- end }}
{{- if .Values.redis.enabled }}
- name: wait-for-redis
  image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  command:
    - bash
    - -c
    - |
      host=$(echo "$REDIS_URL" | sed -E 's#redis://##; s#.*@##; s#:.*##')
      port=$(echo "$REDIS_URL" | sed -E 's#.*:([0-9]+).*#\1#')
      until (echo > "/dev/tcp/${host}/${port}") >/dev/null 2>&1; do
        echo "waiting for redis at ${host}:${port}..."
        sleep 2
      done
      echo "redis is ready"
  envFrom:
    - configMapRef:
        name: {{ include "ownfirebase.fullname" . }}-config
{{- end }}
{{- end -}}
