{{/* Базовое имя чарта */}}
{{- define "aquageo.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Полное имя релиза */}}
{{- define "aquageo.fullname" -}}
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

{{- define "aquageo.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Общие лейблы */}}
{{- define "aquageo.labels" -}}
helm.sh/chart: {{ include "aquageo.chart" . }}
app.kubernetes.io/name: {{ include "aquageo.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/* Selector-лейблы для конкретного компонента: include "aquageo.selectorLabels" (dict "ctx" . "component" "web") */}}
{{- define "aquageo.selectorLabels" -}}
app.kubernetes.io/name: {{ include "aquageo.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "aquageo.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "aquageo.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* Образы */}}
{{- define "aquageo.backendImage" -}}
{{- $tag := .Values.image.backend.tag | default .Chart.AppVersion -}}
{{- printf "%s/%s:%s" .Values.image.registry .Values.image.backend.repository $tag -}}
{{- end -}}

{{- define "aquageo.frontendImage" -}}
{{- $tag := .Values.image.frontend.tag | default .Chart.AppVersion -}}
{{- printf "%s/%s:%s" .Values.image.registry .Values.image.frontend.repository $tag -}}
{{- end -}}

{{/* Имя imagePullSecret (если используется) */}}
{{- define "aquageo.imagePullSecretName" -}}
{{- if .Values.imagePullSecret.existingSecret -}}
{{- .Values.imagePullSecret.existingSecret -}}
{{- else -}}
{{- .Values.imagePullSecret.name -}}
{{- end -}}
{{- end -}}

{{- define "aquageo.imagePullSecrets" -}}
{{- if or .Values.imagePullSecret.create .Values.imagePullSecret.existingSecret }}
imagePullSecrets:
  - name: {{ include "aquageo.imagePullSecretName" . }}
{{- end }}
{{- end -}}

{{/* DATABASE_URL: встроенный postgres или внешняя БД */}}
{{- define "aquageo.databaseUrl" -}}
{{- if .Values.postgres.enabled -}}
{{- printf "postgis://%s:%s@%s-db:%v/%s" .Values.postgres.username .Values.postgres.password (include "aquageo.fullname" .) .Values.postgres.service.port .Values.postgres.database -}}
{{- else if .Values.externalDatabase.url -}}
{{- .Values.externalDatabase.url -}}
{{- else -}}
{{- printf "postgis://%s:%s@%s:%v/%s" .Values.externalDatabase.username .Values.externalDatabase.password .Values.externalDatabase.host .Values.externalDatabase.port .Values.externalDatabase.database -}}
{{- end -}}
{{- end -}}

{{/* REDIS_URL: встроенный redis или внешний */}}
{{- define "aquageo.redisUrl" -}}
{{- if .Values.redis.enabled -}}
{{- printf "redis://%s-redis:%v/0" (include "aquageo.fullname" .) .Values.redis.service.port -}}
{{- else -}}
{{- .Values.externalRedis.url -}}
{{- end -}}
{{- end -}}

{{/* Имя Secret с переменными приложения */}}
{{- define "aquageo.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else -}}
{{- printf "%s-app" (include "aquageo.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/* envFrom для app-контейнеров (configmap + secret) */}}
{{- define "aquageo.appEnvFrom" -}}
envFrom:
  - configMapRef:
      name: {{ include "aquageo.fullname" . }}-env
  - secretRef:
      name: {{ include "aquageo.secretName" . }}
{{- end -}}
