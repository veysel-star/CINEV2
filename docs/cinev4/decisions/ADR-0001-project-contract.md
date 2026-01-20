# ADR-0001: Project-level Contract



## Context



CineV3 sadece shot bazlı doğrulama yapıyordu.

Proje bütünlüğü tanımsızdı.



## Decision



CineV4’te:

- Her proje `project.json` ile tanımlanır

- Shot’lar bu contract altında geçerlidir



## Consequences



+ Proje kimliği netleşir  

+ Release izlenebilir olur  

- Esnek ama kontrolsüz yapı ortadan kalkar



