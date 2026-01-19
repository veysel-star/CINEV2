\# ADR-0002: Shot key == shot.id invariant



\## Context

Shot’lar `shots` dict içinde key ile adresleniyor. İçeride ayrıca `id` alanı var.



\## Decision

Her shot için `shots` içindeki key, `shot.id` ile aynı olmak zorunda.



\## Consequences

\- Tekil kimlik tutarlılığı sağlar.

\- Tool’lar (transition/release) shot id karışıklığı yaşamaz.



\## Alternatives

\- `id` alanını kaldırmak: JSON içeriğinde self-describing özelliği azalır.

\- Key’i görmezden gelmek: veri bütünlüğünü bozar.



