// Renderiza o lado JavaScript de um molde .dc.html sem navegador: extrai o <script> do
// componente, instancia a classe com um DCLogic mínimo, injeta o projeto.json no estado e
// devolve o que renderVals() produz (os estilos e textos que o template receberia).
//
//   node render_molde.mjs <molde.dc.html> <projeto.json> [props em JSON ou -] [sem-dados]
//
// `sem-dados` simula o estado antes do fetch (sem projeto.json carregado).
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const [, , molde, projeto, propsJson, modo] = process.argv;
const html = readFileSync(molde, 'utf8');
const m = html.match(/<script type="text\/x-dc" data-dc-script[^>]*>([\s\S]*?)<\/script>/);
if (!m) throw new Error('molde sem script de componente');

class DCLogic {
  constructor(props) {
    this.props = props ?? {};
    this.state = {};
  }
  setState(s) {
    Object.assign(this.state, s);
  }
}

const fabrica = new vm.Script(`(function (DCLogic) { ${m[1]}\n return Component; })`);
const Component = fabrica.runInNewContext({ console, Math, Date, JSON, parseInt, String, RegExp, Number, Array, Object })(DCLogic);
const c = new Component(propsJson && propsJson !== '-' ? JSON.parse(propsJson) : {});
c.state = { d: modo === 'sem-dados' ? null : JSON.parse(readFileSync(projeto, 'utf8')), erro: null };
console.log(JSON.stringify(c.renderVals()));
