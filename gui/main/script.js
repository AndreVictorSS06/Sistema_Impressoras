// Variável global para armazenar os itens antes de salvar no banco
let itensRelatorio = [];

// --- INICIALIZAÇÃO SEGURA ---
(function() {
    console.log("🚀 Iniciando monitoramento da API Python...");
    
    let retries = 50; 
    let apiInicializada = false; // Trava para evitar dupla execução
    
    async function checkApi() {
        if (apiInicializada) return; // Se já inicializou, ignora
        
        if (window.pywebview && window.pywebview.api) {
            try {
                apiInicializada = true; // Marca como inicializado
                console.log("✅ API Python detectada com sucesso!");

                // Verifica status da conexão/licença para o Toast
                const lic = await pywebview.api.get_license_info();
                if (lic && lic.offline) {
                    if (typeof showToast === "function") {
                        showToast("Sistema sem conexão: validando pelo relógio local.", "error");
                    }
                }
                await carregarImpressoras();
                configurarDataFiltro();
                return true;
            } catch (e) {
                // Silencioso em produção
            }
        }
        
        if (retries > 0) {
            retries--;
            setTimeout(checkApi, 200);
        }
        return false;
    }

    checkApi();
    window.addEventListener("pywebviewready", checkApi);
})();

function configurarDataFiltro() {
  const inputMes = document.getElementById("filtro-mes");
  const agora = new Date();
  
  // Como o sistema salva com competência do mês anterior, 
  // o filtro deve iniciar no mês anterior para mostrar os dados recém-salvos.
  const dataRef = new Date(agora.getFullYear(), agora.getMonth(), 1);
  dataRef.setMonth(dataRef.getMonth() - 1);
  
  const mes = String(dataRef.getMonth() + 1).padStart(2, "0");
  const ano = dataRef.getFullYear();
  inputMes.value = `${ano}-${mes}`;
}

// --- CONTROLE DE ABAS ---
function switchTab(tabName) {
  // Esconde todos os conteúdos
  document
    .querySelectorAll(".tab-content")
    .forEach((tab) => tab.classList.remove("active"));
  // Desativa todos os botões
  document
    .querySelectorAll(".nav-btn")
    .forEach((btn) => btn.classList.remove("active"));

  // Ativa a aba selecionada
  document.getElementById(`tab-${tabName}`).classList.add("active");

  // Ativa o botão correspondente
  const btnAtivo = Array.from(document.querySelectorAll(".nav-btn")).find(
    (btn) => btn.textContent.toLowerCase().includes(tabName.toLowerCase()),
  );
  if (btnAtivo) btnAtivo.classList.add("active");

  // Se for para o histórico, carrega os dados automaticamente
  if (tabName === "historico") {
    atualizarTabelaHistorico();
  }
}

// --- CARREGAR IMPRESSORAS NO SELECT ---
async function carregarImpressoras() {
  const select = document.getElementById("imp-select");
  if (!select) return;
  
  // Limpa opções existentes (exceto a primeira que é o placeholder)
  select.innerHTML = '<option value="" disabled selected>Selecione a Impressora</option>';
  
  const nomes = await pywebview.api.get_impressoras();
  nomes.forEach((nome) => {
    const opt = document.createElement("option");
    opt.value = nome;
    opt.textContent = nome;
    select.appendChild(opt);
  });

  select.addEventListener("change", async () => {
    const nome = select.value;
    const info = await pywebview.api.get_info_impressora(nome);
    document.getElementById("serie").value = info.serie;
    document.getElementById("setor").value = info.setor;

    // Busca a última leitura atual registrada para usar como anterior
    const ultimaLeitura = await pywebview.api.get_ultima_leitura(nome);
    document.getElementById("anterior").value = ultimaLeitura;
  });
}

// --- ADICIONAR REGISTROS NA LISTA TEMPORÁRIA (LIVE TREEVIEW) ---
function enviarRegistroImpressora() {
  const nome = document.getElementById("imp-select").value;
  const ant = parseInt(document.getElementById("anterior").value);
  const atu = parseInt(document.getElementById("atual").value);

  if (!nome || isNaN(ant) || isNaN(atu)) {
    showToast("Preencha todos os campos!", "error");
    return;
  }

  const diferenca = atu - ant;
  const taxa = 0.03; // TODO: Mover para config global
  const custo = diferenca * taxa;

  itensRelatorio.push({
    tipo: "Impressora",
    impressora: nome,
    serie: document.getElementById("serie").value,
    setor: document.getElementById("setor").value,
    leitura_anterior: ant,
    leitura_atual: atu,
    custo: custo,
  });

  atualizarTreeView();

  // LIMPEZA DOS CAMPOS
  document.getElementById("imp-select").value = "";
  document.getElementById("serie").value = "";
  document.getElementById("setor").value = "";
  document.getElementById("anterior").value = "";
  document.getElementById("atual").value = "";

  showToast("Adicionado à lista de conferência!");
}

function enviarComanda() {
  const desc = document.getElementById("comanda-desc").value;
  const val = parseFloat(document.getElementById("comanda-val").value);

  if (!desc || isNaN(val)) {
    showToast("Preencha Descrição e Valor!", "error");
    return;
  }

  itensRelatorio.push({
    tipo: "Comanda",
    descricao: desc,
    tipo_consumo: document.getElementById("comanda-tipo").value,
    setor: document.getElementById("comanda-setor").value,
    valor: val,
  });

  atualizarTreeView();

  // --- LIMPEZA DOS CAMPOS ---
  document.getElementById("comanda-desc").value = "";
  document.getElementById("comanda-tipo").value = "";
  document.getElementById("comanda-setor").value = "";
  document.getElementById("comanda-val").value = "";

  document.getElementById("comanda-desc").focus();
}

// View temporaria para verificar o que vai ser lançado no banco de dados
function atualizarTreeView() {
  const lista = document.getElementById("live-treeview");
  if (!lista) return;
  lista.innerHTML = "";

  if (itensRelatorio.length === 0) {
    lista.innerHTML = '<li class="empty-msg">Nenhum item adicionado.</li>';
    return;
  }

  itensRelatorio.forEach((item, index) => {
    const li = document.createElement("li");
    li.style.cssText =
      "display:flex; justify-content:space-between; align-items:center; padding:8px; border-bottom:1px solid #eee;";

    // CORREÇÃO DO BUG: Se não houver 'custo' (Comanda), ele busca 'valor'.
    const valorParaExibir =
      item.custo !== undefined ? item.custo : item.valor || 0;

    li.innerHTML = `
            <span><b>${item.tipo}:</b> ${item.impressora || item.descricao} - R$ ${Number(valorParaExibir).toFixed(2)}</span>
            <div>
                <button onclick="editarItemTemporario(${index})" style="background:none; border:none; cursor:pointer;">✏️</button>
                <button onclick="excluirItemTemporario(${index})" style="background:none; border:none; cursor:pointer;">❌</button>
            </div>
        `;
    lista.appendChild(li);
  });
}

// Remove o item da lista antes de gerar o relatório final na View
function excluirItemTemporario(index) {
  itensRelatorio.splice(index, 1);
  atualizarTreeView();
  showToast("Item removido", "error");
}

// Devolve os dados para os campos de entrada para correção
function editarItemTemporario(index) {
  const item = itensRelatorio[index];

  if (item.tipo === "Impressora") {
    switchTab("registro");
    document.getElementById("imp-select").value = item.impressora;
    document.getElementById("serie").value = item.serie;
    document.getElementById("setor").value = item.setor;
    document.getElementById("anterior").value = item.leitura_anterior;
    document.getElementById("atual").value = item.leitura_atual;
  } else {
    switchTab("registro"); // Certifique-se que o id da aba de comandas seja este ou altere aqui
    document.getElementById("comanda-desc").value = item.descricao;
    document.getElementById("comanda-tipo").value = item.tipo_consumo;
    document.getElementById("comanda-setor").value = item.setor;
    document.getElementById("comanda-val").value = item.valor;
  }

  // Remove da lista para não duplicar ao salvar a correção
  itensRelatorio.splice(index, 1);
  atualizarTreeView();

  showToast("Item carregado para edição", "success");
}

// 2. Ajuste na função de Gerar Relatório para "Carimbar" a data certa
async function gerarRelatorio() {
  if (itensRelatorio.length === 0) {
    showToast("Adicione itens primeiro!", "error");
    return;
  }

  const btn = document.querySelector(".btn-gerar"); // Ajuste o seletor se for outro
  if (btn) btn.disabled = true;

  // Pega a data do mês passado para salvar no banco
  const dataRef = new Date();
  dataRef.setMonth(dataRef.getMonth() - 1);
  const dataFinalStr = dataRef.toISOString().split("T")[0] + " 12:00:00";

  // Prepara os dados enviando a data retroativa
  const dadosComData = itensRelatorio.map((item) => ({
    ...item,
    data: dataFinalStr,
  }));

  try {
    const resp = await pywebview.api.salvar_lote_no_banco(dadosComData);
    if (resp.status === "success") {
      showToast(
        `Salvo no histórico de ${dataRef.toLocaleDateString("pt-BR", { month: "long" })}!`,
        "success",
      );
      itensRelatorio = [];
      atualizarTreeView();
    }
  } catch (err) {
    showToast("Erro ao salvar dados.", "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

// --- HISTÓRICO (BUSCA NO BANCO) ---
async function atualizarTabelaHistorico() {
  try {
    const inputMes = document.getElementById("filtro-mes");
    const tbody = document.getElementById("corpo-tabela-historico");
    if (!inputMes || !tbody) return;

    const mesSelecionado = inputMes.value;

    // --- 1. ATUALIZAÇÃO DOS CARDS DO DASHBOARD ---
    try {
      const resumo = await pywebview.api.get_resumo_mes(mesSelecionado);

      // Usamos o operador || 0 para garantir que, se o resumo vier vazio, mostre zero
      const totalImp = Number(resumo?.total_impressoras || 0);
      const totalCom = Number(resumo?.total_comandas || 0);
      const totalGer = Number(resumo?.total_geral || 0);
      const totalPag = Number(resumo?.total_paginas || 0);

      document.getElementById("dash-imp").innerText =
        `R$ ${totalImp.toFixed(2)}`;
      document.getElementById("dash-com").innerText =
        `R$ ${totalCom.toFixed(2)}`;
      document.getElementById("dash-geral").innerText =
        `R$ ${totalGer.toFixed(2)}`;
      document.getElementById("dash-paginas").innerText =
        totalPag.toLocaleString("pt-BR");
    } catch (err) {
      console.error("Erro ao carregar resumo do dashboard:", err);
      // Caso dê erro na API, resetamos os cards para evitar confusão visual
      document.getElementById("dash-imp").innerText = "R$ 0.00";
      document.getElementById("dash-com").innerText = "R$ 0.00";
      document.getElementById("dash-geral").innerText = "R$ 0.00";
      document.getElementById("dash-paginas").innerText = "0";
    }

    // --- 2. CARREGAMENTO DA TABELA ---
    const registros = await pywebview.api.get_historico(mesSelecionado);
    tbody.innerHTML = "";

    if (!registros || registros.length === 0) {
      tbody.innerHTML =
        "<tr><td colspan='4' style='text-align:center; padding:20px; color: #666;'>Nenhum dado encontrado para este mês.</td></tr>";

      // Se não há registros na tabela, forçamos os cards a zero também por segurança
      document.getElementById("dash-imp").innerText = "R$ 0.00";
      document.getElementById("dash-com").innerText = "R$ 0.00";
      document.getElementById("dash-geral").innerText = "R$ 0.00";
      document.getElementById("dash-paginas").innerText = "0";
      return;
    }

    registros.forEach((item) => {
      // Mapeamento dos índices conforme seu banco: [tipo, nome, serie, setor, ant, atu, valor]
      const tipo = item[0] || "N/A";
      const nome = item[1] || "Sem Nome";
      const setor = item[3] || "Geral";
      const valor = Number(item[6] || 0);

      const isComanda = tipo.toLowerCase() === "comanda";
      const row = document.createElement("tr");

      row.innerHTML = `
                <td style="padding: 12px;">
                    <span style="background: ${isComanda ? "#dcfce7" : "#dbeafe"}; 
                                 color: ${isComanda ? "#166534" : "#1e40af"}; 
                                 padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 11px;">
                        ${tipo.toUpperCase()}
                    </span>
                </td>
                <td style="padding: 12px; font-weight: 500;">${nome}</td>
                <td style="padding: 12px; color: #666;">${setor}</td>
                <td style="padding: 12px; font-weight: bold;">R$ ${valor.toFixed(2)}</td>
            `;
      tbody.appendChild(row);
    });
  } catch (error) {
    console.error("Erro geral no Histórico:", error);
  }
}

// --- EXPORTAR EXCEL ---
async function exportarParaExcel() {
  try {
    const inputMes = document.getElementById("filtro-mes").value;
    const registros = await pywebview.api.get_historico(inputMes);

    if (!registros || registros.length === 0) return alert("Sem dados.");

    let rows = [
      ["RELATÓRIO DE CONSUMO - SERRANA"],
      [`Mês: ${inputMes}`],
      [],
      ["IMPRESSORAS"],
      [
        "Nome",
        "Série",
        "Setor",
        "Anterior",
        "Atual",
        "Diferença",
        "Custo (R$)",
      ],
    ];

    let subImp = 0;

    registros
      .filter((r) => r[0] === "Impressora")
      .forEach((r) => {
        const ant = Number(r[4] || 0);
        const atu = Number(r[5] || 0);
        const dif = atu - ant;
        const custo = Number(r[6] || 0);
        rows.push([r[1], r[2], r[3], ant, atu, dif, custo.toFixed(2)]);
        subImp += custo;
      });

    rows.push(["", "", "", "", "", "Subtotal:", subImp.toFixed(2)], []);

    rows.push(["COMANDAS"], ["Nome", "Tipo Consumo", "Setor", "Valor (R$)"]);
    let subCom = 0;
    registros
      .filter((r) => r[0] === "Comanda")
      .forEach((r) => {
        const valor = Number(r[6] || 0);
        rows.push([r[1], r[7] || "", r[3], valor.toFixed(2)]);
        subCom += valor;
      });

    rows.push(["", "", "Subtotal:", subCom.toFixed(2)], []);

    const totalGeral = subImp + subCom;
    rows.push(["TOTAL GERAL:", "", "", "R$ " + totalGeral.toFixed(2)]);

    const ws = XLSX.utils.aoa_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Consumo");
    const b64 = XLSX.write(wb, { bookType: "xlsx", type: "base64" });
    await pywebview.api.salvar_arquivo_excel(b64, `Relatorio_${inputMes}.xlsx`);
  } catch (e) {
    alert("Erro: " + e.message);
  }
}

// --- TOAST NOTIFICATIONS ---
function showToast(mensagem, tipo = "success") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText =
      "position: fixed; bottom: 20px; right: 20px; z-index: 9999;";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${tipo}`;
  toast.style.cssText = `
        background: #333; color: white; padding: 12px 20px; border-radius: 8px;
        margin-top: 10px; display: flex; align-items: center; gap: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2); font-family: sans-serif;
        border-left: 5px solid ${tipo === "success" ? "#28a745" : "#dc3545"};
        transition: opacity 0.5s;
    `;

  toast.innerHTML = `<span>${tipo === "success" ? "✅" : "❌"}</span><span>${mensagem}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 500);
  }, 3000);
}

// --- ABA CONFIGURAÇÕES ---
async function carregarInfoLicenca() {
  try {
    const r = await pywebview.api.get_license_info();
    const sourceLabel = {
      internet: "Internet (NTP) ✓",
      local: "Relógio local (offline)",
      stamp: "Carimbo salvo (offline)",
    };
    document.getElementById("cfg-expiry").textContent = r.expiry_date || "—";
    document.getElementById("cfg-current").textContent = r.current_date || "—";
    document.getElementById("cfg-source").textContent =
      sourceLabel[r.source] || r.source || "—";

    const warnEl = document.getElementById("cfg-offline-warn");
    if (warnEl) warnEl.style.display = r.offline ? "block" : "none";
  } catch (e) {
    console.error("Erro ao carregar info de licença:", e);
  }
}

async function renovarLicenca() {
  const senhaInput = document.getElementById("cfg-senha");
  const resultDiv = document.getElementById("cfg-resultado");
  const senha = senhaInput.value.trim();

  if (!senha) {
    showToast("Digite a senha de renovação.", "error");
    return;
  }

  if (resultDiv) resultDiv.style.display = "none";

  try {
    const resp = await pywebview.api.renovar_licenca(senha);

    if (resultDiv) {
      resultDiv.style.display = "block";
      if (resp.ok) {
        resultDiv.style.cssText =
          "display:block; padding:12px 16px; border-radius:8px; " +
          "background:#f0fdf4; border:1px solid #bbf7d0; color:#166534; font-size:14px;";
        resultDiv.innerHTML = "✅ " + resp.message;
        senhaInput.value = "";
        carregarInfoLicenca();
        showToast(resp.message, "success");
      } else {
        resultDiv.style.cssText =
          "display:block; padding:12px 16px; border-radius:8px; " +
          "background:#fef2f2; border:1px solid #fecaca; color:#991b1b; font-size:14px;";
        resultDiv.innerHTML = "❌ " + resp.message;
        senhaInput.value = "";
        senhaInput.focus();
      }
    }
  } catch (e) {
    showToast("Erro ao comunicar com o servidor.", "error");
  }
}

// Carrega info de licença ao abrir a aba config
const _origSwitchTab = switchTab;
switchTab = function (tabName) {
  _origSwitchTab(tabName);
  if (tabName === "config") carregarInfoLicenca();
};

function atualizarInfoCompetencia() {
  const agora = new Date();

  // Forçamos para o dia 1 do mês atual antes de subtrair.
  // Isso evita bugs em dias 29, 30 e 31.
  const d = new Date(agora.getFullYear(), agora.getMonth(), 1);
  d.setMonth(d.getMonth() - 1);

  const meses = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
  ];

  const label = document.getElementById("aviso-competencia");
  if (label) {
    label.innerHTML = `📌 Lançamento para: <strong>${meses[d.getMonth()]} / ${d.getFullYear()}</strong>`;
  }

  return d;
}

// 3. Inicialização ao carregar a página
document.addEventListener("DOMContentLoaded", () => {
  // Define o aviso visual do mês de referência
  atualizarInfoCompetencia();

  // Configura o filtro do histórico para já abrir no mês passado
  const filtroData = document.getElementById("filtro-mes-ano");
  if (filtroData) {
    const d = new Date();
    d.setMonth(d.getMonth() - 1);
    const mes = String(d.getMonth() + 1).padStart(2, "0");
    const ano = d.getFullYear();
    filtroData.value = `${ano}-${mes}`;
  }

  // Delay para o Python inicializar o banco antes da primeira busca
  setTimeout(() => {
    if (typeof atualizarTabelaHistorico === "function") atualizarTabelaHistorico();
  }, 600);
});

async function prepararImpressaoPDF() {
  const mesReferencia = document.getElementById("filtro-mes").value;

  if (!mesReferencia) {
    showToast("Selecione um mês primeiro!", "error");
    return;
  }

  try {
    // 1. Busca os dados consolidados do banco (garante que o PDF seja fiel ao histórico)
    const registros = await pywebview.api.get_historico(mesReferencia);
    const resumo = await pywebview.api.get_resumo_mes(mesReferencia);

    if (!registros || registros.length === 0) {
      showToast("Não há dados salvos para este mês.", "error");
      return;
    }

    // 2. Prepara o objeto exatamente como o api.py espera
    const dadosParaPython = {
      mes: mesReferencia,
      total_imp: resumo.total_impressoras.toFixed(2),
      total_com: resumo.total_comandas.toFixed(2),
      total_paginas: resumo.total_paginas.toString(),
      total_geral: resumo.total_geral.toFixed(2),
      itens: registros.map((r) => ({
        tipo: r[0], // 'Impressora' ou 'Comanda'
        desc: r[1],
        tipo_consumo: r[0] === 'Comanda' ? (r[7] || "-") : "-",
        setor: r[3], // Setor
        serie: r[2] || "-", // Série
        anterior: r[4] || "-",
        atual: r[5] || "-",
        consumo: r[5] && r[4] ? r[5] - r[4] : "-",
        valor: Number(r[6]).toFixed(2),
      })),
    };

    showToast("Gerando visualização do PDF...", "success");

    // 3. Chama a função unificada no Python (preparar_impressao_pdf)
    const sucesso = await pywebview.api.preparar_impressao_pdf(dadosParaPython);

    if (!sucesso) {
      showToast("Erro ao processar arquivo no sistema.", "error");
    }
  } catch (error) {
    console.error("Erro ao preparar PDF:", error);
    showToast("Erro interno ao gerar relatório.", "error");
  }
}
