/*
 * Service worker do Edital Aberto.
 *
 * A casca do app (HTML, ícones, fontes) fica em cache e abre instantâneo,
 * mesmo sem sinal. Já `dados.json` é sempre buscado na rede primeiro, porque
 * é o arquivo que precisa estar fresco; se a rede falhar, devolve a última
 * coleta guardada e o app avisa na tela que está mostrando dado antigo.
 */

var VERSAO = "edital-aberto-v3";
var CASCA = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icone-180.png",
  "./icone-192.png",
  "./icone-512.png"
];

self.addEventListener("install", function (evento) {
  evento.waitUntil(
    caches.open(VERSAO)
      .then(function (cache) { return cache.addAll(CASCA); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (evento) {
  evento.waitUntil(
    caches.keys()
      .then(function (nomes) {
        return Promise.all(nomes.map(function (nome) {
          return nome === VERSAO ? null : caches.delete(nome);
        }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

function guardar(pedido, resposta) {
  if (!resposta || !resposta.ok) return resposta;
  var copia = resposta.clone();
  caches.open(VERSAO).then(function (cache) { cache.put(pedido, copia); });
  return resposta;
}

self.addEventListener("fetch", function (evento) {
  var pedido = evento.request;
  if (pedido.method !== "GET") return;

  var url = new URL(pedido.url);

  // Os dados: rede primeiro, cache como rede de segurança.
  if (url.pathname.endsWith("/dados.json")) {
    evento.respondWith(
      fetch(pedido)
        .then(function (resposta) { return guardar("dados.json", resposta); })
        .catch(function () { return caches.match("dados.json"); })
    );
    return;
  }

  // Navegação: entrega a casca em cache e revalida por baixo.
  if (pedido.mode === "navigate") {
    evento.respondWith(
      caches.match("./index.html").then(function (guardado) {
        var daRede = fetch(pedido)
          .then(function (resposta) { return guardar("./index.html", resposta); })
          .catch(function () { return guardado; });
        return guardado || daRede;
      })
    );
    return;
  }

  // Ícones e fontes: cache primeiro.
  evento.respondWith(
    caches.match(pedido).then(function (guardado) {
      return guardado || fetch(pedido)
        .then(function (resposta) { return guardar(pedido, resposta); })
        .catch(function () { return guardado; });
    })
  );
});
