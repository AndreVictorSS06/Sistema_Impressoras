const sourceLabel = {
  internet: "Internet (NTP) ✓",
  local: "Relógio local (offline)",
  stamp: "Carimbo salvo (offline)",
};

// Função para processar a renovação
async function tentarRenovar() {
  const input = document.getElementById("input-senha");
  const status = document.getElementById("status-renovacao");
  const senha = input.value;

  if (!senha) return;

  status.style.color = "#888";
  status.textContent = "Validando código...";

  try {
    // Chama a função no seu api.py
    const r = await window.pywebview.api.renovar_licenca(senha);

    if (r.ok) {
      status.style.color = "#2ecc71";
      status.textContent = "Sucesso! Reiniciando...";

      // Pequeno delay para o usuário ler a mensagem de sucesso
      setTimeout(() => {
        window.location.href = "index.html";
      }, 1500);
    } else {
      status.style.color = "#e74c3c";
      status.textContent = r.message;
      input.value = "";
      input.focus();
    }
  } catch (e) {
    status.textContent = "Erro de conexão com o sistema.";
    console.error(e);
  }
}

window.addEventListener("pywebviewready", async () => {
  // 1. Preenche as informações da licença no card de fundo (Imediato)
  try {
    const r = await window.pywebview.api.get_license_info();

    document.getElementById("expiry-date").textContent = r.expiry_date;
    document.getElementById("current-date").textContent = r.current_date;
    document.getElementById("source").textContent =
      sourceLabel[r.source] || r.source;

    const badge = document.getElementById("status-badge");
    const text = document.getElementById("status-text");

    if (r.clock_tampered) {
      badge.className = "badge tampered";
      text.textContent = "⚠ Relógio do sistema adulterado";
    } else if (r.offline) {
      badge.className = "badge offline";
      text.textContent = "Verificado offline";
    } else {
      badge.className = "badge expired";
      text.textContent = "Licença expirada";
    }
  } catch (e) {
    document.getElementById("status-text").textContent =
      "Erro ao verificar licença";
  }

  // 2. Configura a exibição do Popup com Delay (A sua ideia brilhante)
  const overlay = document.getElementById("overlay");
  const btn = document.getElementById("btn-ativar");
  const input = document.getElementById("input-senha");

  // Garante que o overlay comece escondido (caso não tenha mudado no CSS)
  if (overlay) overlay.style.display = "none";

  setTimeout(() => {
    if (overlay && input) {
      overlay.style.display = "flex"; // Mostra o popup centralizado
      input.focus(); // Dá foco automático no campo

      // Ativa uma transição suave se você tiver definido no CSS
      overlay.style.opacity = "1";
    }
  }, 4000); // 4000ms = 4 segundos de leitura antes do popup

  // 3. Configura os eventos (Enter e Clique)
  if (btn && input) {
    btn.addEventListener("click", tentarRenovar);

    input.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        tentarRenovar();
      }
    });
  }
});
