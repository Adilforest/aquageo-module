# Деплой AquaGeo (Helm + Argo CD)

Helm-чарт для модуля портала водных ресурсов: Django/DRF + Celery (worker/beat),
Redis, PostGIS и React-фронтенд. Образы собираются в приватный **ghcr.io**
(workflow `.github/workflows/build-images.yml`), доставка — через **Argo CD**.

## Структура

```
deploy/
  helm/aquageo/        # сам чарт
    Chart.yaml
    values.yaml        # дефолты (демо: встроенные postgres+redis)
    values-prod.yaml   # пример прод-оверрайда (внешняя БД/Redis, ingress, TLS)
    templates/
  argocd/application.yaml   # пример Argo CD Application
```

## Безопасность

App-поды (web/worker/beat/frontend/migrate-job) и redis работают под строгим
контекстом:

- `runAsNonRoot: true`, `runAsUser/Group: 65532`, `fsGroup: 65532` (uid+gid > 60000, fs ≥ 65000);
- `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`;
- `seccompProfile: RuntimeDefault`.

Запись только в `emptyDir` (`/tmp`, `staticfiles`, `mediafiles`, beat-schedule).
Встроенный PostGIS не умеет read-only/uid 65532, поэтому получает минимальный
контекст (`fsGroup: 999`, drop ALL). **Для прода используйте внешний managed
Postgres** (`postgres.enabled=false` + `externalDatabase.url`).

## Быстрый старт (демо, встроенные БД/Redis)

```bash
helm upgrade --install aquageo deploy/helm/aquageo \
  --namespace aquageo --create-namespace \
  --set secrets.secretKey="$(openssl rand -hex 32)" \
  --set secrets.geminiApiKey="<key>" \
  --set image.backend.tag=latest --set image.frontend.tag=latest
```

Приватный registry — создать pull-секрет:

```bash
# вариант A: чарт создаёт секрет сам
helm ... --set imagePullSecret.create=true \
         --set imagePullSecret.username=<gh-user> \
         --set imagePullSecret.token=<PAT read:packages>

# вариант B: заранее созданный секрет
kubectl -n aquageo create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io --docker-username=<gh-user> --docker-password=<PAT>
helm ... --set imagePullSecret.existingSecret=ghcr-pull
```

## Прод через Argo CD

1. Сделать GHCR-пакеты `aquageo-backend`/`aquageo-frontend` приватными
   (Settings → Packages → Change visibility).
2. Создать в namespace `aquageo` секреты `aquageo-app` (SECRET_KEY, DATABASE_URL,
   GEMINI_API_KEY) и `ghcr-pull`.
3. Применить `deploy/argocd/application.yaml` (поправив repoURL/host).

migrate-job помечен `helm.sh/hook: pre-install,pre-upgrade` и
`argocd.argoproj.io/hook: PreSync` — миграции прогоняются до синка.

## Проверка локально

```bash
helm lint deploy/helm/aquageo
helm template aquageo deploy/helm/aquageo | kubectl apply --dry-run=client -f -
```
