const codeInput = document.getElementById("code");
const result = document.getElementById("result");
chrome.storage.local.get(["homeToken"], ({homeToken}) => {
  if (homeToken) codeInput.value = homeToken;
});
document.getElementById("save").addEventListener("click", async () => {
  const token = codeInput.value.trim();
  if (token.length < 32) { result.textContent = "Código inválido."; return; }
  await chrome.storage.local.set({homeToken:token});
  result.textContent = "Código salvo neste navegador.";
});
document.getElementById("share").addEventListener("click", async () => {
  result.textContent = "Compartilhando...";
  try {
    const token = codeInput.value.trim();
    if (token.length < 32) throw new Error("Cole o código fornecido pelo Home primeiro.");
    const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
    if (!tab?.id || !/^https?:\/\//.test(tab.url || "")) {
      throw new Error("Abra uma página http(s) comum antes de compartilhar.");
    }
    const injection = await chrome.scripting.executeScript({
      target:{tabId:tab.id},
      func:() => ({
        title: document.title || "",
        url: location.href,
        text: (document.body?.innerText || "").slice(0,5000)
      })
    });
    const page = injection[0]?.result;
    if (!page) throw new Error("Não foi possível ler esta aba.");
    const response = await fetch("http://127.0.0.1:48731/share", {
      method:"POST",
      headers:{"Content-Type":"application/json","X-Home-Token":token},
      body:JSON.stringify(page)
    });
    const responseData = await response.json();
    if (!response.ok) throw new Error(responseData.message || "Home indisponível.");
    await chrome.storage.local.set({homeToken:token});
    result.textContent = "Esta aba foi compartilhada com o Home.";
  } catch(err) {
    result.textContent = "Erro: " + (err.message || String(err));
  }
});
document.getElementById("tabs").addEventListener("click", async () => {
  const list = document.getElementById("tabList");
  list.replaceChildren();
  const allowed = await chrome.permissions.request({permissions:["tabs"]});
  if (!allowed) { result.textContent = "Permissão de abas não concedida."; return; }
  const tabs = await chrome.tabs.query({currentWindow:true});
  for (const tab of tabs.slice(0,60)) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = (tab.title || "Aba sem título").slice(0,80);
    button.addEventListener("click", async () => {
      await chrome.tabs.update(tab.id,{active:true});
      result.textContent = "Aba selecionada. Abra novamente a extensão nessa aba para compartilhar.";
    });
    list.appendChild(button);
  }
});
