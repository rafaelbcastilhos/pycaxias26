# Frontend da loja PyCaxias

Frontend estático, sem framework, que usa a API local em `http://127.0.0.1:5000`.
Não abra o `index.html` diretamente como `file://`: sirva a página por HTTP para
que o navegador permita as chamadas à API local e disponibilize o WebMCP.

Com a API já em execução, sirva estes arquivos em outro terminal:

```bash
python3 -m http.server 8000
```

Abra `http://127.0.0.1:8000`. Para usar outro endereço de API, abra a página com
`?api=http://127.0.0.1:5000`.

## WebMCP

Em navegadores com suporte a WebMCP, a página registra seis ferramentas em
`document.modelContext`: `search_products`, `get_order`, `create_order`,
`pay_order`, `cancel_order` e `restock_product`. As ferramentas usam a mesma
API e atualizam a tela visível após a chamada. Navegadores sem WebMCP continuam
com toda a interface manual disponível.
