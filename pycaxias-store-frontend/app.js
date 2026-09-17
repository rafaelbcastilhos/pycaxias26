const API_URL = new URLSearchParams(window.location.search).get("api") || "http://127.0.0.1:5000";
const productList = document.querySelector("#product-list");
const toast = document.querySelector("#toast");
const apiStatus = document.querySelector("#api-status");
const webMcpStatus = document.querySelector("#webmcp-status");

function key(prefix) {
  return `${prefix}-${crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}${Math.random()}`.replace(/[^\w-]/g, "")}`;
}

function notify(message, error = false) {
  toast.textContent = message;
  toast.className = `toast visible${error ? " error" : ""}`;
  window.clearTimeout(notify.timeout);
  notify.timeout = window.setTimeout(() => { toast.className = "toast"; }, 3600);
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Accept: "application/json", ...options.headers },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error?.message || "Não foi possível concluir a operação.");
  return data;
}

function formatProduct(product) {
  const available = product.stock > 0;
  return `<article class="product${available ? "" : " soldout"}">
    <span>${product.sku}</span><h3>${product.name}</h3><p>${product.description}</p>
    <div class="product-meta"><div><div class="price">R$ ${product.price}</div><small>${product.stock} em estoque</small></div>
    <button ${available ? "" : "disabled"} data-sku="${product.sku}">${available ? "Selecionar" : "Esgotado"}</button></div></article>`;
}

function renderProducts(products) {
  productList.innerHTML = products.length
    ? products.map(formatProduct).join("")
    : '<p class="empty">Nenhum produto encontrado.</p>';
}

async function loadProducts(query = "") {
  productList.innerHTML = '<p class="empty">Carregando catálogo…</p>';
  try {
    const products = await request(`/v1/products?query=${encodeURIComponent(query)}&limit=20`);
    renderProducts(products);
    apiStatus.textContent = "API: online";
    apiStatus.classList.add("online");
  } catch (error) {
    productList.innerHTML = '<p class="empty">A API local não está disponível.</p>';
    apiStatus.textContent = "API: offline";
    apiStatus.classList.remove("online");
  }
}

async function showOrder(orderId) {
  const output = document.querySelector("#order-result");
  try {
    const order = await request(`/v1/orders/${encodeURIComponent(orderId)}`);
    output.innerHTML = `<strong>${order.product_name}</strong><br>${order.quantity} unidade(s) · R$ ${order.total}<br>Status: <strong>${order.status}</strong>`;
    if (order.status === "PENDING") output.innerHTML += `<div class="order-actions"><button data-pay="${order.order_id}">Pagar</button><button class="cancel" data-cancel="${order.order_id}">Cancelar</button></div>`;
    if (order.status === "PAID") output.innerHTML += `<div class="order-actions"><button class="cancel" data-cancel="${order.order_id}">Cancelar pedido</button></div>`;
  } catch (error) { output.textContent = error.message; }
}

document.querySelector("#search-form").addEventListener("submit", (event) => { event.preventDefault(); loadProducts(new FormData(event.currentTarget).get("query")); });
document.querySelector("#product-list").addEventListener("click", (event) => { const sku = event.target.dataset.sku; if (sku) { document.querySelector("#order-sku").value = sku; document.querySelector("#order-form").scrollIntoView({ behavior: "smooth", block: "center" }); } });
document.querySelector("#order-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); try { const order = await request("/v1/orders", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": key("web-order") }, body: JSON.stringify({ sku: form.get("sku"), quantity: Number(form.get("quantity")) }) }); document.querySelector("#order-id").value = order.order_id; await showOrder(order.order_id); notify(`Pedido ${order.order_id} criado.`); loadProducts(); } catch (error) { notify(error.message, true); } });
document.querySelector("#lookup-form").addEventListener("submit", (event) => { event.preventDefault(); showOrder(new FormData(event.currentTarget).get("order_id")); });
document.querySelector("#order-result").addEventListener("click", async (event) => { const orderId = event.target.dataset.pay || event.target.dataset.cancel; if (!orderId) return; const action = event.target.dataset.pay ? "payment" : "cancellation"; try { await request(`/v1/orders/${orderId}/${action}`, { method: "POST", headers: event.target.dataset.pay ? { "Idempotency-Key": key("web-pay") } : {} }); await showOrder(orderId); notify(event.target.dataset.pay ? "Pagamento confirmado." : "Pedido cancelado."); loadProducts(); } catch (error) { notify(error.message, true); } });
document.querySelector("#restock-form").addEventListener("submit", async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); try { const product = await request(`/v1/products/${encodeURIComponent(form.get("sku"))}/restock`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ units: Number(form.get("units")) }) }); notify(`${product.name}: estoque atualizado para ${product.stock}.`); loadProducts(); } catch (error) { notify(error.message, true); } });

const productSchema = {
  type: "object",
  properties: {
    query: { type: "string", maxLength: 100, description: "Texto para buscar por nome, descrição ou SKU." },
    limit: { type: "integer", minimum: 1, maximum: 20, default: 5, description: "Máximo de produtos retornados." },
  },
  additionalProperties: false,
};
const orderIdSchema = { type: "string", pattern: "^ORD-[0-9a-f]{16}$", description: "Identificador do pedido." };
const skuSchema = { type: "string", pattern: "^[A-Z]{3}-[0-9]{4}$", description: "SKU do produto." };

async function executeWebMcp(action) {
  try {
    return await action();
  } catch (error) {
    notify(error.message, true);
    throw error;
  }
}

async function registerWebMcpTools() {
  const modelContext = document.modelContext;
  if (!modelContext?.registerTool) {
    webMcpStatus.textContent = "WebMCP: indisponível";
    return;
  }

  const readOnly = { readOnlyHint: true, untrustedContentHint: false, consequentialHint: false };
  const write = { readOnlyHint: false, untrustedContentHint: false, consequentialHint: true };
  const tools = [
    {
      name: "search_products",
      title: "Buscar produtos",
      description: "Busca produtos ativos no catálogo PyCaxias por nome, descrição ou SKU. Não altera o estado da loja.",
      inputSchema: productSchema,
      annotations: readOnly,
      execute: ({ query = "", limit = 5 }, options) => executeWebMcp(async () => {
        const products = await request(`/v1/products?query=${encodeURIComponent(query)}&limit=${limit}`, { signal: options?.signal });
        renderProducts(products);
        return products;
      }),
    },
    {
      name: "get_order",
      title: "Consultar pedido",
      description: "Retorna o status e os valores de um pedido existente. Não altera o estado da loja.",
      inputSchema: { type: "object", properties: { order_id: orderIdSchema }, required: ["order_id"], additionalProperties: false },
      annotations: readOnly,
      execute: ({ order_id }, options) => executeWebMcp(async () => {
        const order = await request(`/v1/orders/${encodeURIComponent(order_id)}`, { signal: options?.signal });
        document.querySelector("#order-id").value = order.order_id;
        await showOrder(order.order_id);
        return order;
      }),
    },
    {
      name: "create_order",
      title: "Criar pedido",
      description: "Cria um pedido PENDING e reserva estoque para o SKU e quantidade informados. O preço é definido pelo catálogo e não pode ser informado.",
      inputSchema: { type: "object", properties: { sku: skuSchema, quantity: { type: "integer", minimum: 1, maximum: 100, description: "Unidades desejadas; a loja aplica o limite por pedido." } }, required: ["sku", "quantity"], additionalProperties: false },
      annotations: write,
      execute: ({ sku, quantity }, options) => executeWebMcp(async () => {
        const order = await request("/v1/orders", { method: "POST", signal: options?.signal, headers: { "Content-Type": "application/json", "Idempotency-Key": key("webmcp-order") }, body: JSON.stringify({ sku, quantity }) });
        document.querySelector("#order-sku").value = sku;
        document.querySelector("#order-id").value = order.order_id;
        await showOrder(order.order_id);
        loadProducts();
        return order;
      }),
    },
    {
      name: "pay_order",
      title: "Pagar pedido",
      description: "Confirma o pagamento de um pedido PENDING existente. Esta ação altera o status do pedido para PAID.",
      inputSchema: { type: "object", properties: { order_id: orderIdSchema }, required: ["order_id"], additionalProperties: false },
      annotations: write,
      execute: ({ order_id }, options) => executeWebMcp(async () => {
        const order = await request(`/v1/orders/${encodeURIComponent(order_id)}/payment`, { method: "POST", signal: options?.signal, headers: { "Idempotency-Key": key("webmcp-pay") } });
        await showOrder(order.order_id);
        return order;
      }),
    },
    {
      name: "cancel_order",
      title: "Cancelar pedido",
      description: "Cancela um pedido PENDING ou PAID e devolve as unidades reservadas ao estoque. A operação é irreversível.",
      inputSchema: { type: "object", properties: { order_id: orderIdSchema }, required: ["order_id"], additionalProperties: false },
      annotations: write,
      execute: ({ order_id }, options) => executeWebMcp(async () => {
        const order = await request(`/v1/orders/${encodeURIComponent(order_id)}/cancellation`, { method: "POST", signal: options?.signal });
        await showOrder(order.order_id);
        loadProducts();
        return order;
      }),
    },
    {
      name: "restock_product",
      title: "Repor estoque",
      description: "Acrescenta unidades ao estoque do produto. Repetir a chamada acrescenta as unidades novamente.",
      inputSchema: { type: "object", properties: { sku: skuSchema, units: { type: "integer", minimum: 1, maximum: 1000, description: "Unidades a acrescentar." } }, required: ["sku", "units"], additionalProperties: false },
      annotations: write,
      execute: ({ sku, units }, options) => executeWebMcp(async () => {
        const product = await request(`/v1/products/${encodeURIComponent(sku)}/restock`, { method: "POST", signal: options?.signal, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ units }) });
        document.querySelector("#restock-sku").value = sku;
        document.querySelector("#restock-units").value = units;
        loadProducts();
        return product;
      }),
    },
  ];

  try {
    await Promise.all(tools.map((tool) => modelContext.registerTool(tool)));
    webMcpStatus.textContent = `WebMCP: ${tools.length} ferramentas`;
    webMcpStatus.classList.add("online");
  } catch (error) {
    webMcpStatus.textContent = "WebMCP: não autorizado";
    console.warn("Não foi possível registrar as ferramentas WebMCP.", error);
  }
}

loadProducts();
if (document.readyState === "complete") registerWebMcpTools();
else window.addEventListener("load", registerWebMcpTools, { once: true });
