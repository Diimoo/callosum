{{/*
Expand the name of the chart.
*/}}
{{- define "callosum.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "callosum.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "callosum.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "callosum.labels" -}}
helm.sh/chart: {{ include "callosum.chart" . }}
{{ include "callosum.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "callosum.selectorLabels" -}}
app.kubernetes.io/name: {{ include "callosum.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "callosum.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "callosum.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Set secret name
*/}}
{{- define "callosum.secretName" -}}
{{- default .secretName .existingSecret }}
{{- end }}

{{/*
Create env vars from secrets
*/}}
{{- define "callosum.envSecrets" -}}
    {{- range $secretSuffix, $secretContent := .Values.auth }}
    {{- if and (ne $secretContent.enabled false) ($secretContent.secretKeys) }}
    {{- range $name, $key := $secretContent.secretKeys }}
- name: {{ $name | upper | replace "-" "_" | quote }}
  valueFrom:
    secretKeyRef:
      name: {{ include "callosum.secretName" $secretContent }}
      key: {{ default $name $key }}
    {{- end }}
    {{- end }}
    {{- end }}
{{- end }}

{{/*
Helpers for mounting a psql convenience script into pods.
*/}}
{{- define "callosum.pgInto.enabled" -}}
{{- if and .Values.tooling .Values.tooling.pgInto .Values.tooling.pgInto.enabled }}true{{- end }}
{{- end }}

{{- define "callosum.pgInto.configMapName" -}}
{{- printf "%s-pginto" (include "callosum.fullname" .) -}}
{{- end }}

{{- define "callosum.pgInto.checksumAnnotation" -}}
{{- if (include "callosum.pgInto.enabled" .) }}
checksum/pginto: {{ include (print $.Template.BasePath "/tooling-pginto-configmap.yaml") . | sha256sum }}
{{- end }}
{{- end }}

{{- define "callosum.pgInto.volumeMount" -}}
{{- if (include "callosum.pgInto.enabled" .) }}
- name: pginto-script
  mountPath: {{ default "/usr/local/bin/pginto" .Values.tooling.pgInto.mountPath }}
  subPath: pginto
  readOnly: true
{{- end }}
{{- end }}

{{- define "callosum.pgInto.volume" -}}
{{- if (include "callosum.pgInto.enabled" .) }}
- name: pginto-script
  configMap:
    name: {{ include "callosum.pgInto.configMapName" . }}
    defaultMode: 0755
{{- end }}
{{- end }}

{{- define "callosum.renderVolumeMounts" -}}
{{- $pginto := include "callosum.pgInto.volumeMount" .ctx -}}
{{- $existing := .volumeMounts -}}
{{- if or $pginto $existing -}}
volumeMounts:
{{- if $pginto }}
{{ $pginto | nindent 2 }}
{{- end }}
{{- if $existing }}
{{ toYaml $existing | nindent 2 }}
{{- end }}
{{- end -}}
{{- end }}

{{- define "callosum.renderVolumes" -}}
{{- $pginto := include "callosum.pgInto.volume" .ctx -}}
{{- $existing := .volumes -}}
{{- if or $pginto $existing -}}
volumes:
{{- if $pginto }}
{{ $pginto | nindent 2 }}
{{- end }}
{{- if $existing }}
{{ toYaml $existing | nindent 2 }}
{{- end }}
{{- end -}}
{{- end }}

{{/*
Return the configured autoscaling engine; defaults to HPA when unset.
*/}}
{{- define "callosum.autoscaling.engine" -}}
{{- $engine := default "hpa" .Values.autoscaling.engine -}}
{{- $engine | lower -}}
{{- end }}
