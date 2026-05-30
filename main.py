import os, sys, datetime, traceback

_ERROR_LOG = None

def _log_error(msg):
    global _ERROR_LOG
    try:
        if not _ERROR_LOG:
            if 'EXTERNAL_STORAGE' in os.environ:
                _ERROR_LOG = os.path.join(os.environ['EXTERNAL_STORAGE'], 'Lena_Servicos_Error.log')
            else:
                _ERROR_LOG = '/storage/emulated/0/Lena_Servicos_Error.log'
        with open(_ERROR_LOG, 'a') as f:
            f.write(f'{datetime.datetime.now()}: {msg}\n')
    except:
        pass

def excepthook(tp, val, tb):
    _log_error(f'UNHANDLED: {tp.__name__}: {val}\n{"".join(traceback.format_exception(tp, val, tb))}')

sys.excepthook = excepthook

os.environ['KIVY_NO_ARGS'] = '1'

from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.gridlayout import GridLayout

from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView

import sqlite3

_db_path = None

def set_db_path(path):
    global _db_path; _db_path = path

def get_db_path():
    global _db_path
    if _db_path: return _db_path
    app = MDApp.get_running_app()
    db_dir = app.user_data_dir if platform == 'android' else os.path.join(os.path.expanduser('~'), 'Lena Servicos')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'dados.db')

def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS funcionarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS turnos (id INTEGER PRIMARY KEY AUTOINCREMENT, funcionario_id INTEGER, turno TEXT, data TEXT, valor REAL, FOREIGN KEY(funcionario_id) REFERENCES funcionarios(id))')
    conn.execute('CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)')
    conn.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('valor_manha', '120.00')")
    conn.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('valor_noite', '100.00')")
    conn.commit(); conn.close()

def obter_config(chave, padrao=None):
    try:
        conn = get_db()
        row = conn.execute("SELECT valor FROM configuracoes WHERE chave=?", (chave,)).fetchone()
        conn.close()
        return row['valor'] if row else padrao
    except: return padrao

def definir_config(chave, valor):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?,?)", (chave, str(valor)))
    conn.commit(); conn.close()

def get_func_by_nome(nome):
    conn = get_db()
    row = conn.execute("SELECT * FROM funcionarios WHERE LOWER(nome)=LOWER(?)", (nome,)).fetchone()
    conn.close()
    return dict(row) if row else None

def cadastrar_func(nome):
    if not nome or not nome.strip(): raise ValueError('Nome vazio.')
    nome = nome.strip()
    if get_func_by_nome(nome): raise ValueError(f"'{nome}' ja existe.")
    conn = get_db()
    conn.execute("INSERT INTO funcionarios (nome) VALUES (?)", (nome,))
    conn.commit(); conn.close()

def listar_funcs():
    conn = get_db()
    rows = conn.execute("SELECT nome FROM funcionarios ORDER BY nome").fetchall()
    conn.close()
    return [r['nome'] for r in rows]

def excluir_func(nome):
    func = get_func_by_nome(nome)
    if not func: raise ValueError(f"'{nome}' nao encontrado.")
    conn = get_db()
    conn.execute("DELETE FROM turnos WHERE funcionario_id=?", (func['id'],))
    conn.execute("DELETE FROM funcionarios WHERE id=?", (func['id'],))
    conn.commit(); conn.close()

def obter_valor_turno(turno):
    try:
        v = obter_config(f'valor_{turno}')
        return float(v) if v else (120.0 if turno == 'manha' else 100.0)
    except: return 120.0 if turno == 'manha' else 100.0

def registrar_turno(nome_func, turno, data=None):
    if turno not in ['manha','noite']: raise ValueError('Turno invalido.')
    func = get_func_by_nome(nome_func)
    if not func: raise ValueError(f"'{nome_func}' nao encontrado.")
    valor = obter_valor_turno(turno)
    if not data: data = datetime.date.today().isoformat()
    conn = get_db()
    if conn.execute("SELECT id FROM turnos WHERE funcionario_id=? AND data=? AND turno=?", (func['id'], data, turno)).fetchone():
        conn.close()
        tn = 'Manha' if turno == 'manha' else 'Noite'
        raise ValueError(f"'{nome_func}' ja tem turno {tn} em {data}.")
    conn.execute("INSERT INTO turnos VALUES (NULL,?,?,?,?)", (func['id'], turno, data, valor))
    conn.commit(); conn.close()

def listar_turnos(di=None, df=None):
    conn = get_db()
    conds = []; params = []
    if di: conds.append("t.data>=?"); params.append(di)
    if df: conds.append("t.data<=?"); params.append(df)
    q = "SELECT t.id, f.nome as func, t.turno, t.data, t.valor FROM turnos t JOIN funcionarios f ON t.funcionario_id = f.id"
    if conds: q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY t.data DESC, t.id DESC"
    rows = conn.execute(q, tuple(params)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def atualizar_turno(tid, nova_data, novo_nome):
    func = get_func_by_nome(novo_nome)
    if not func: raise ValueError(f"'{novo_nome}' nao encontrado.")
    conn = get_db()
    row = conn.execute("SELECT turno FROM turnos WHERE id=?", (tid,)).fetchone()
    if not row: conn.close(); raise ValueError('Turno nao encontrado.')
    turno = row['turno']
    if conn.execute("SELECT id FROM turnos WHERE funcionario_id=? AND data=? AND turno=? AND id!=?", (func['id'], nova_data, turno, tid)).fetchone():
        conn.close()
        tn = 'Manha' if turno == 'manha' else 'Noite'
        raise ValueError(f"'{novo_nome}' ja tem {tn} em {nova_data}.")
    conn.execute("UPDATE turnos SET data=?, funcionario_id=? WHERE id=?", (nova_data, func['id'], tid))
    conn.commit(); conn.close()

def excluir_turno(tid):
    conn = get_db()
    conn.execute("DELETE FROM turnos WHERE id=?", (tid,))
    conn.commit(); conn.close()

# ==================== RELATORIO / PDF ====================

def gerar_pdf(dados, caminho=None):
    from fpdf import FPDF
    pdf = FPDF(); pdf.add_page()
    fn = 'Helvetica'
    pdf.set_fill_color(10,10,10); pdf.rect(0,0,210,297,'F')
    pdf.set_draw_color(212,175,55); pdf.set_line_width(1.5)
    pdf.set_fill_color(20,18,12)
    pdf.polygon([(0,0),(45,0),(0,45)],style='F'); pdf.line(0,45,45,0)
    pdf.polygon([(210,0),(165,0),(210,45)],style='F'); pdf.line(165,0,210,45)
    pdf.ln(15)
    pdf.set_text_color(212,175,55); pdf.set_font(fn,size=24,style='B')
    pdf.cell(0,10,'LENA SERVICOS',ln=True,align='C')
    pdf.set_text_color(255,255,255); pdf.set_font(fn,size=10,style='B')
    pdf.cell(0,8,'R E L A T O R I O   D E   P A G A M E N T O',ln=True,align='C'); pdf.ln(5)
    if dados.get('di') and dados.get('df'):
        try:
            di=datetime.datetime.strptime(dados['di'],'%Y-%m-%d').strftime('%d/%m/%Y')
            df=datetime.datetime.strptime(dados['df'],'%Y-%m-%d').strftime('%d/%m/%Y')
            pdf.set_text_color(160,160,160); pdf.set_font(fn,9)
            pdf.cell(0,5,f'Periodo: {di} ate {df}',ln=True,align='C')
        except: pass
    pdf.ln(4)
    pdf.set_fill_color(28,28,30); pdf.set_draw_color(38,38,40); pdf.set_line_width(0.3)
    pdf.rect(15,66,180,20,style='DF')
    pdf.set_xy(20,70); pdf.set_text_color(212,175,55); pdf.set_font(fn,14,style='B')
    pdf.cell(0,8,dados['nome'].upper(),ln=True)
    pdf.ln(6)
    pdf.set_x(15); pdf.set_text_color(212,175,55); pdf.set_font(fn,10,style='B')
    pdf.cell(0,6,'DETALHAMENTO DOS DIAS TRABALHADOS',ln=True); pdf.ln(3)
    pdf.set_x(15); pdf.set_text_color(212,175,55); pdf.set_font(fn,8,style='B')
    pdf.cell(60,6,'DATA',align='C'); pdf.cell(60,6,'TURNO',align='C'); pdf.cell(60,6,'VALOR',align='C',ln=True); pdf.ln(2)
    for i,t in enumerate(dados['turnos']):
        if i>0 and i%12==0:
            pdf.add_page(); pdf.set_fill_color(10,10,10); pdf.rect(0,0,210,297,'F')
            pdf.set_draw_color(212,175,55); pdf.line(0,45,45,0); pdf.line(165,0,210,45); pdf.ln(15)
            pdf.set_x(15); pdf.set_text_color(212,175,55); pdf.set_font(fn,8,style='B')
            pdf.cell(60,6,'DATA',align='C'); pdf.cell(60,6,'TURNO',align='C'); pdf.cell(60,6,'VALOR',align='C',ln=True); pdf.ln(2)
        y=pdf.get_y(); pdf.set_fill_color(28,28,30); pdf.set_draw_color(38,38,40)
        pdf.rect(15,y,180,9,style='DF')
        try: dt=datetime.datetime.strptime(t['data'],'%Y-%m-%d').strftime('%d/%m/%Y')
        except: dt=t['data']
        pdf.set_xy(22,y+2.5); pdf.set_text_color(255,255,255); pdf.set_font(fn,9); pdf.cell(45,4,dt)
        pdf.set_xy(97,y+2.5); pdf.cell(38,4,'Manha' if t['turno']=='manha' else 'Noite')
        pdf.set_xy(135,y+2.5); pdf.set_font(fn,9,style='B'); pdf.cell(60,4,f'R$ {t["valor"]:.2f}',align='C')
        pdf.ln(7.5)
    pdf.ln(8)
    if pdf.get_y()>215:
        pdf.add_page(); pdf.set_fill_color(10,10,10); pdf.rect(0,0,210,297,'F')
        pdf.set_draw_color(212,175,55); pdf.line(0,45,45,0); pdf.line(165,0,210,45); pdf.ln(15)
    y=pdf.get_y()
    pdf.set_fill_color(28,28,30); pdf.set_draw_color(38,38,40)
    pdf.rect(15,y,56,18,style='DF')
    pdf.set_xy(18,y+3); pdf.set_text_color(212,175,55); pdf.set_font(fn,6,style='B')
    pdf.cell(50,3,'DIAS (DIA)',ln=True)
    pdf.set_xy(18,y+6); pdf.set_text_color(255,255,255); pdf.set_font(fn,12,style='B')
    pdf.cell(50,6,str(dados['dm']),ln=True)
    pdf.rect(77,y,56,18,style='DF')
    pdf.set_xy(80,y+3); pdf.set_text_color(212,175,55); pdf.set_font(fn,6,style='B')
    pdf.cell(50,3,'DIAS (NOITE)',ln=True)
    pdf.set_xy(80,y+6); pdf.set_text_color(255,255,255); pdf.set_font(fn,12,style='B')
    pdf.cell(50,6,str(dados['dn']),ln=True)
    pdf.set_fill_color(28,28,30); pdf.set_draw_color(212,175,55); pdf.set_line_width(0.7)
    pdf.rect(139,y,56,18,style='DF')
    pdf.set_xy(142,y+3); pdf.set_text_color(212,175,55); pdf.set_font(fn,6,style='B')
    pdf.cell(50,3,'VALOR TOTAL',ln=True)
    pdf.set_xy(142,y+6); pdf.set_text_color(255,255,255); pdf.set_font(fn,12,style='B')
    pdf.cell(50,6,f'R$ {dados["vt"]:.2f}',ln=True)
    pdf.ln(24)
    if not caminho:
        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                base = primary_external_storage_path()
                if base: pasta = os.path.join(base, 'Lena Servicos')
                else: pasta = os.path.join(MDApp.get_running_app().user_data_dir, 'Lena Servicos')
            except:
                pasta = os.path.join(MDApp.get_running_app().user_data_dir, 'Lena Servicos')
        else:
            pasta = os.path.join(os.path.expanduser('~'), 'Lena Servicos')
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, f"Relatorio_{dados['nome'].replace(' ','_')}.pdf")
    pdf.output(caminho)
    return caminho

def copiar_wpp(dados):
    periodo = ''
    if dados.get('di') and dados.get('df'):
        try:
            di=datetime.datetime.strptime(dados['di'],'%Y-%m-%d').strftime('%d/%m/%Y')
            df=datetime.datetime.strptime(dados['df'],'%Y-%m-%d').strftime('%d/%m/%Y')
            periodo = f" *Periodo:* {di} ate {df}"
        except: pass
    texto = f"*Nome:* {dados['nome']}.{periodo}\n*Dias (dia):* {dados['dm']}\n*Dias (noite):* {dados['dn']}\n*Valor:* R$ {dados['vt']:.2f}."
    try:
        from plyer import clipboard
        clipboard.copy(texto)
    except:
        pass
    return texto

# ==================== TELAS ====================
class MenuScreen(Screen):
    def on_enter(self): MDApp.get_running_app().atualizar_funcs()

class CadastroScreen(Screen):
    def cadastrar(self):
        nome = self.ids.nome.text.strip()
        if not nome: MDSnackbar(text='Digite um nome.', bg_color=(0.8,0.2,0.2,1)).open(); return
        try:
            cadastrar_func(nome)
            self.ids.nome.text = ''
            MDSnackbar(text=f"'{nome}' cadastrado!", bg_color=(0.3,0.7,0.3,1)).open()
            self.manager.current = 'menu'
        except Exception as e: MDSnackbar(text=str(e), bg_color=(0.8,0.2,0.2,1)).open()

class RegistrarScreen(Screen):
    def on_enter(self):
        app = MDApp.get_running_app()
        self.ids.data.text = datetime.date.today().isoformat()
        self.turno = 'manha'
        if app.funcs: self.ids.func_btn.text = app.funcs[0]
        vm = obter_config('valor_manha','120.00')
        self.ids.turno_btn.text = f"Manha (R$ {float(vm):.2f})"
    def abrir_func(self):
        app = MDApp.get_running_app()
        MDDropdownMenu(caller=self.ids.func_btn, items=[{'text':n,'viewclass':'OneLineListItem','on_release':lambda n=n: setattr(self.ids.func_btn,'text',n)} for n in app.funcs] or [{'text':'Nenhum','viewclass':'OneLineListItem'}], width_mult=4).open()
    def abrir_turno(self):
        vm=obter_config('valor_manha','120.00'); vn=obter_config('valor_noite','100.00')
        MDDropdownMenu(caller=self.ids.turno_btn, items=[{'text':f"Manha (R$ {float(vm):.2f})",'viewclass':'OneLineListItem','on_release':lambda: self.sel_turno('manha')},{'text':f"Noite (R$ {float(vn):.2f})",'viewclass':'OneLineListItem','on_release':lambda: self.sel_turno('noite')}], width_mult=4).open()
    def sel_turno(self, t):
        self.turno = t
        v=obter_config(f'valor_{t}','120.00' if t=='manha' else '100.00')
        self.ids.turno_btn.text=f"{'Manha' if t=='manha' else 'Noite'} (R$ {float(v):.2f})"
    def registrar(self):
        nome=self.ids.func_btn.text; data=self.ids.data.text.strip()
        if nome in ['','Nenhum','Selecione']: MDSnackbar(text='Selecione funcionario.', bg_color=(0.8,0.2,0.2,1)).open(); return
        if data:
            try: datetime.datetime.strptime(data,'%Y-%m-%d')
            except: MDSnackbar(text='Data invalida.', bg_color=(0.8,0.2,0.2,1)).open(); return
        else: data=None
        try: registrar_turno(nome,self.turno,data); MDSnackbar(text='Registrado!', bg_color=(0.3,0.7,0.3,1)).open(); self.manager.current='menu'
        except Exception as e: MDSnackbar(text=str(e), bg_color=(0.8,0.2,0.2,1)).open()

class RelatorioScreen(Screen):
    def on_enter(self):
        app=MDApp.get_running_app()
        self.ids.di.text=datetime.date.today().replace(day=1).isoformat()
        self.ids.df.text=datetime.date.today().isoformat()
        self.ids.result.text='Preencha e clique em Buscar'
        self.dados=None
        if app.funcs: self.ids.func_btn.text=app.funcs[0]
    def abrir_func(self):
        app=MDApp.get_running_app()
        MDDropdownMenu(caller=self.ids.func_btn, items=[{'text':n,'viewclass':'OneLineListItem','on_release':lambda n=n: setattr(self.ids.func_btn,'text',n)} for n in app.funcs] or [{'text':'Nenhum','viewclass':'OneLineListItem'}], width_mult=4).open()
    def buscar(self):
        nome=self.ids.func_btn.text
        if nome in ['','Nenhum','Selecione']: MDSnackbar(text='Selecione funcionario.', bg_color=(0.8,0.2,0.2,1)).open(); return
        di=self.ids.di.text.strip(); df=self.ids.df.text.strip()
        for d in [di,df]:
            if d:
                try: datetime.datetime.strptime(d,'%Y-%m-%d')
                except: MDSnackbar(text='Data invalida.', bg_color=(0.8,0.2,0.2,1)).open(); return
        try:
            func=get_func_by_nome(nome)
            if not func: raise ValueError(f"'{nome}' nao encontrado.")
            conn=get_db()
            q="SELECT * FROM turnos WHERE funcionario_id=?"; p=[func['id']]
            if di: q+=" AND data>=?"; p.append(di)
            if df: q+=" AND data<=?"; p.append(df)
            q+=" ORDER BY data"
            turnos=[dict(r) for r in conn.execute(q,tuple(p)).fetchall()]; conn.close()
            if not turnos: raise ValueError(f"Nenhum registro no periodo.")
            dm=sum(1 for t in turnos if t['turno']=='manha'); dn=sum(1 for t in turnos if t['turno']=='noite'); vt=sum(t['valor'] for t in turnos)
            self.dados={'nome':func['nome'],'dm':dm,'dn':dn,'vt':vt,'turnos':turnos,'di':di,'df':df}
            self.ids.result.text=f"[b]Nome:[/b] {func['nome']}\n[b]Dias (Dia):[/b] {dm}\n[b]Dias (Noite):[/b] {dn}\n[color=#D4AF37][b]Valor: R$ {vt:.2f}[/b][/color]"
            MDSnackbar(text='Dados carregados!', bg_color=(0.3,0.7,0.3,1)).open()
        except Exception as e: self.dados=None; self.ids.result.text=f'[color=#FF6B6B]{str(e)}[/color]'; MDSnackbar(text=str(e), bg_color=(0.8,0.2,0.2,1)).open()
    def pdf(self):
        if not self.dados: MDSnackbar(text='Busque primeiro.', bg_color=(0.8,0.2,0.2,1)).open(); return
        try: gerar_pdf(self.dados); MDSnackbar(text='PDF salvo em Lena Servicos!', bg_color=(0.3,0.7,0.3,1)).open()
        except Exception as e: MDSnackbar(text=str(e), bg_color=(0.8,0.2,0.2,1)).open()
    def wpp(self):
        if not self.dados: MDSnackbar(text='Busque primeiro.', bg_color=(0.8,0.2,0.2,1)).open(); return
        try: copiar_wpp(self.dados); MDSnackbar(text='Copiado! Cole no WhatsApp.', bg_color=(0.3,0.7,0.3,1)).open()
        except Exception as e: MDSnackbar(text=str(e), bg_color=(0.8,0.2,0.2,1)).open()

class EditarScreen(Screen):
    def on_enter(self):
        self.tid=None; self.ids.nova_data.text=''
        app=MDApp.get_running_app()
        if app.funcs: self.ids.func_btn.text=app.funcs[0]
        self.carregar_turnos()
    def carregar_turnos(self):
        try:
            ts=listar_turnos()
            if ts:
                t=ts[0]; tn='Manha' if t['turno']=='manha' else 'Noite'
                self.ids.turno_btn.text=f"ID:{t['id']} {t['data']} {t['func']} {tn}"; self.tid=t['id']
            else: self.ids.turno_btn.text='Nenhum turno'; self.tid=None
        except: self.ids.turno_btn.text='Erro'; self.tid=None
    def abrir_turnos(self):
        ts=listar_turnos()
        MDDropdownMenu(caller=self.ids.turno_btn, items=[{'text':f"ID:{t['id']} {t['data']} {t['func']} {'Manha' if t['turno']=='manha' else 'Noite'}",'viewclass':'OneLineListItem','on_release':lambda t=t: (setattr(self.ids.turno_btn,'text',f"ID:{t['id']} {t['data']} {t['func']} {'Manha' if t['turno']=='manha' else 'Noite'}"),setattr(self,'tid',t['id']))} for t in ts] or [{'text':'Nenhum','viewclass':'OneLineListItem'}], width_mult=4).open()
    def abrir_func(self):
        app=MDApp.get_running_app()
        MDDropdownMenu(caller=self.ids.func_btn, items=[{'text':n,'viewclass':'OneLineListItem','on_release':lambda n=n: setattr(self.ids.func_btn,'text',n)} for n in app.funcs] or [{'text':'Nenhum','viewclass':'OneLineListItem'}], width_mult=4).open()
    def salvar(self):
        if not self.tid: MDSnackbar(text='Selecione turno.', bg_color=(0.8,0.2,0.2,1)).open(); return
        nd=self.ids.nova_data.text.strip(); nn=self.ids.func_btn.text
        if not nd:
            p=self.ids.turno_btn.text.split(' ')
            nd=p[1] if len(p)>1 else datetime.date.today().isoformat()
        try: atualizar_turno(self.tid,nd,nn); self.ids.nova_data.text=''; MDSnackbar(text='Atualizado!', bg_color=(0.3,0.7,0.3,1)).open(); self.manager.current='menu'
        except Exception as e: MDSnackbar(text=str(e), bg_color=(0.8,0.2,0.2,1)).open()
    def excluir(self):
        nome=self.ids.func_btn.text
        if nome in ['','Nenhum','Selecione']: MDSnackbar(text='Selecione funcionario.', bg_color=(0.8,0.2,0.2,1)).open(); return
        d=MDDialog(title='Excluir',text=f"Excluir '{nome}' e todos registros?",buttons=[MDFlatButton(text='Cancelar',on_release=lambda x:d.dismiss()),MDFlatButton(text='Excluir',theme_text_color='Custom',text_color=(1,0.4,0.4,1),on_release=lambda x:(d.dismiss(),self.conf_excluir(nome)))])
        d.open()
    def conf_excluir(self,nome):
        try: excluir_func(nome); MDSnackbar(text='Excluido!', bg_color=(0.3,0.7,0.3,1)).open(); self.manager.current='menu'
        except Exception as e: MDSnackbar(text=str(e), bg_color=(0.8,0.2,0.2,1)).open()

class ConfigScreen(Screen):
    def on_enter(self):
        self.ids.vm.text=f"{float(obter_config('valor_manha','120.00')):.2f}"
        self.ids.vn.text=f"{float(obter_config('valor_noite','100.00')):.2f}"
    def salvar(self):
        try:
            vm=float(self.ids.vm.text.strip().replace(',','.')); vn=float(self.ids.vn.text.strip().replace(',','.'))
            definir_config('valor_manha',f'{vm:.2f}'); definir_config('valor_noite',f'{vn:.2f}')
            MDSnackbar(text='Salvo!', bg_color=(0.3,0.7,0.3,1)).open(); self.manager.current='menu'
        except: MDSnackbar(text='Valores invalidos.', bg_color=(0.8,0.2,0.2,1)).open()

class App(MDApp):
    def __init__(self,**kwargs):
        super().__init__(**kwargs); self.funcs=[]
    def on_start(self):
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            except:
                pass
    def build(self):
        from kivy.core.window import Window
        Window.softinput_mode = 'below_target'
        self.theme_cls.theme_style='Dark'; self.theme_cls.primary_palette='Yellow'
        try:
            if platform == 'android':
                db_dir = self.user_data_dir
            else:
                db_dir = os.path.join(os.path.expanduser('~'), 'Lena Servicos')
            os.makedirs(db_dir, exist_ok=True)
            set_db_path(os.path.join(db_dir, 'dados.db'))
            init_db()
        except Exception as e:
            _log_error(f'INIT FAILED: {e}\n{traceback.format_exc()}')
        sm=ScreenManager(transition=SlideTransition())
        # Menu
        m=MenuScreen(name='menu')
        box=MDBoxLayout(orientation='vertical',md_bg_color=(0.04,0.04,0.04,1),spacing=dp(10),padding=dp(20))
        box.add_widget(MDLabel(text='LENA SERVICOS',font_style='H4',bold=True,halign='center',theme_text_color='Custom',text_color=(0.83,0.69,0.22,1),size_hint_y=None,height=dp(50)))
        box.add_widget(MDLabel(text='Gestao de Funcionarios',font_style='Body1',halign='center',theme_text_color='Custom',text_color=(0.63,0.63,0.63,1),size_hint_y=None,height=dp(30)))
        grid=GridLayout(cols=2,spacing=dp(15),padding=dp(5),adaptive_height=True,pos_hint={'center_y':0.5})
        for icone,label,sub,scr in [
            ('👥','Cadastrar','Funcionario','cadastro'),('📝','Registrar','Turno','registrar'),
            ('📊','Relatorio','Pagamentos','relatorio'),('✏️','Alterar','Registro','editar')]:
            card=MDCard(orientation='vertical',md_bg_color=(0.11,0.11,0.12,1),radius=dp(12),size_hint_y=None,height=dp(140),on_release=lambda s=scr: setattr(sm,'current',s))
            card.add_widget(MDLabel(text=icone,font_style='H3',halign='center',size_hint_y=None,height=dp(50),pos_hint={'center_y':0.6}))
            card.add_widget(MDLabel(text=label,font_style='Subtitle1',bold=True,halign='center',theme_text_color='Custom',text_color=(0.83,0.69,0.22,1)))
            card.add_widget(MDLabel(text=sub,font_style='Caption',halign='center',theme_text_color='Custom',text_color=(0.83,0.69,0.22,1)))
            grid.add_widget(card)
        box.add_widget(grid)
        box.add_widget(MDRaisedButton(text='⚙️ Ajustar Precos',theme_bg_color='Custom',md_bg_color=(0.11,0.11,0.12,1),theme_text_color='Custom',text_color=(0.83,0.69,0.22,1),size_hint_x=0.5,pos_hint={'center_x':0.5},on_release=lambda: setattr(sm,'current','config')))
        m.add_widget(box)
        sm.add_widget(m)
        # Cadastro
        c=CadastroScreen(name='cadastro')
        cb=MDBoxLayout(orientation='vertical',md_bg_color=(0.04,0.04,0.04,1),spacing=dp(10),padding=dp(20))
        cb.add_widget(MDRaisedButton(text='← Voltar',theme_bg_color='Custom',md_bg_color=(0.04,0.04,0.04,1),theme_text_color='Custom',text_color=(0.63,0.63,0.63,1),size_hint_x=None,width=dp(100),on_release=lambda: setattr(sm,'current','menu')))
        card=MDCard(orientation='vertical',md_bg_color=(0.11,0.11,0.12,1),radius=dp(12),padding=dp(20),spacing=dp(15),size_hint_y=None,height=dp(250),pos_hint={'center_x':0.5},size_hint_x=0.9)
        card.add_widget(MDLabel(text='👥 Cadastrar Funcionario',font_style='H5',bold=True,halign='center',theme_text_color='Custom',text_color=(0.83,0.69,0.22,1)))
        tf=MDTextField(hint_text='Nome completo',mode='rectangle',color_mode='custom',line_color_focus=(0.83,0.69,0.22,1))
        c.ids['nome']=tf; card.add_widget(tf)
        card.add_widget(MDRaisedButton(text='Salvar',md_bg_color=(0.83,0.69,0.22,1),theme_text_color='Custom',text_color=(0,0,0,1),pos_hint={'center_x':0.5},size_hint_x=0.7,on_release=lambda: c.cadastrar()))
        cb.add_widget(card); c.add_widget(cb)
        sm.add_widget(c)
        # Registrar
        r=RegistrarScreen(name='registrar')
        rb=MDBoxLayout(orientation='vertical',md_bg_color=(0.04,0.04,0.04,1),spacing=dp(10),padding=dp(20))
        rb.add_widget(MDRaisedButton(text='← Voltar',theme_bg_color='Custom',md_bg_color=(0.04,0.04,0.04,1),theme_text_color='Custom',text_color=(0.63,0.63,0.63,1),size_hint_x=None,width=dp(100),on_release=lambda: setattr(sm,'current','menu')))
        card=MDCard(orientation='vertical',md_bg_color=(0.11,0.11,0.12,1),radius=dp(12),padding=dp(20),spacing=dp(12),size_hint_y=None,height=dp(380),pos_hint={'center_x':0.5},size_hint_x=0.9)
        card.add_widget(MDLabel(text='📝 Registrar Turno',font_style='H5',bold=True,halign='center',theme_text_color='Custom',text_color=(0.83,0.69,0.22,1)))
        fb=MDRaisedButton(text='Selecione',theme_bg_color='Custom',md_bg_color=(0.15,0.15,0.16,1),size_hint_x=1,on_release=lambda: r.abrir_func())
        r.ids['func_btn']=fb; card.add_widget(fb)
        tb=MDRaisedButton(text='Manha',theme_bg_color='Custom',md_bg_color=(0.15,0.15,0.16,1),size_hint_x=1,on_release=lambda: r.abrir_turno())
        r.ids['turno_btn']=tb; card.add_widget(tb)
        tf=MDTextField(hint_text='Data (AAAA-MM-DD)',mode='rectangle',color_mode='custom',line_color_focus=(0.83,0.69,0.22,1))
        r.ids['data']=tf; card.add_widget(tf)
        card.add_widget(MDRaisedButton(text='Registrar',md_bg_color=(0.83,0.69,0.22,1),theme_text_color='Custom',text_color=(0,0,0,1),pos_hint={'center_x':0.5},size_hint_x=0.7,on_release=lambda: r.registrar()))
        rb.add_widget(card); r.add_widget(rb)
        sm.add_widget(r)
        # Relatorio
        rl=RelatorioScreen(name='relatorio')
        rlb=MDBoxLayout(orientation='vertical',md_bg_color=(0.04,0.04,0.04,1),spacing=dp(8),padding=dp(15))
        rlb.add_widget(MDRaisedButton(text='← Voltar',theme_bg_color='Custom',md_bg_color=(0.04,0.04,0.04,1),theme_text_color='Custom',text_color=(0.63,0.63,0.63,1),size_hint_x=None,width=dp(100),on_release=lambda: setattr(sm,'current','menu')))
        rlb.add_widget(MDLabel(text='📊 Relatorio',font_style='H6',bold=True,halign='center',theme_text_color='Custom',text_color=(0.83,0.69,0.22,1),size_hint_y=None,height=dp(35)))
        hb=MDBoxLayout(orientation='horizontal',adaptive_height=True,spacing=dp(5))
        fb2=MDRaisedButton(text='Funcionario',theme_bg_color='Custom',md_bg_color=(0.15,0.15,0.16,1),size_hint_x=0.4,on_release=lambda: rl.abrir_func())
        rl.ids['func_btn']=fb2; hb.add_widget(fb2)
        di=MDTextField(hint_text='Inicio',mode='rectangle',size_hint_x=0.3,color_mode='custom',line_color_focus=(0.83,0.69,0.22,1))
        rl.ids['di']=di; hb.add_widget(di)
        df=MDTextField(hint_text='Fim',mode='rectangle',size_hint_x=0.3,color_mode='custom',line_color_focus=(0.83,0.69,0.22,1))
        rl.ids['df']=df; hb.add_widget(df)
        rlb.add_widget(hb)
        rlb.add_widget(MDRaisedButton(text='Buscar',md_bg_color=(0.83,0.69,0.22,1),theme_text_color='Custom',text_color=(0,0,0,1),size_hint_x=0.5,pos_hint={'center_x':0.5},on_release=lambda: rl.buscar()))
        sv=MDScrollView(size_hint_y=None,height=dp(180),do_scroll_x=False)
        lbl=MDLabel(id='result',text='Preencha e clique em Buscar',markup=True,font_style='Body1',size_hint_y=None,height=dp(180),halign='center',valign='top',theme_text_color='Custom',text_color=(1,1,1,1),padding=(dp(10),dp(10)))
        rl.ids['result']=lbl; sv.add_widget(lbl); rlb.add_widget(sv)
        rlb.add_widget(MDRaisedButton(text='📄 Exportar PDF',theme_bg_color='Custom',md_bg_color=(0.15,0.15,0.16,1),theme_text_color='Custom',text_color=(0.83,0.69,0.22,1),size_hint_x=0.7,pos_hint={'center_x':0.5},on_release=lambda: rl.pdf()))
        rlb.add_widget(MDRaisedButton(text='📋 Copiar WhatsApp',theme_bg_color='Custom',md_bg_color=(0.15,0.15,0.16,1),theme_text_color='Custom',text_color=(0.83,0.69,0.22,1),size_hint_x=0.7,pos_hint={'center_x':0.5},on_release=lambda: rl.wpp()))
        rl.add_widget(rlb)
        sm.add_widget(rl)
        # Editar
        e=EditarScreen(name='editar')
        eb=MDBoxLayout(orientation='vertical',md_bg_color=(0.04,0.04,0.04,1),spacing=dp(10),padding=dp(20))
        eb.add_widget(MDRaisedButton(text='← Voltar',theme_bg_color='Custom',md_bg_color=(0.04,0.04,0.04,1),theme_text_color='Custom',text_color=(0.63,0.63,0.63,1),size_hint_x=None,width=dp(100),on_release=lambda: setattr(sm,'current','menu')))
        card=MDCard(orientation='vertical',md_bg_color=(0.11,0.11,0.12,1),radius=dp(12),padding=dp(20),spacing=dp(12),size_hint_y=None,height=dp(400),pos_hint={'center_x':0.5},size_hint_x=0.9)
        card.add_widget(MDLabel(text='✏️ Alterar Registro',font_style='H5',bold=True,halign='center',theme_text_color='Custom',text_color=(0.83,0.69,0.22,1)))
        tb2=MDRaisedButton(text='Carregando...',theme_bg_color='Custom',md_bg_color=(0.15,0.15,0.16,1),size_hint_x=1,on_release=lambda: e.abrir_turnos())
        e.ids['turno_btn']=tb2; card.add_widget(tb2)
        nd=MDTextField(hint_text='Nova Data (AAAA-MM-DD)',mode='rectangle',color_mode='custom',line_color_focus=(0.83,0.69,0.22,1))
        e.ids['nova_data']=nd; card.add_widget(nd)
        fb3=MDRaisedButton(text='Funcionario',theme_bg_color='Custom',md_bg_color=(0.15,0.15,0.16,1),size_hint_x=1,on_release=lambda: e.abrir_func())
        e.ids['func_btn']=fb3; card.add_widget(fb3)
        card.add_widget(MDRaisedButton(text='Salvar Alteracao',md_bg_color=(0.83,0.69,0.22,1),theme_text_color='Custom',text_color=(0,0,0,1),size_hint_x=0.8,pos_hint={'center_x':0.5},on_release=lambda: e.salvar()))
        card.add_widget(MDRaisedButton(text='Excluir Funcionario',theme_bg_color='Custom',md_bg_color=(0.15,0.15,0.16,1),theme_text_color='Custom',text_color=(1,0.4,0.4,1),size_hint_x=0.8,pos_hint={'center_x':0.5},on_release=lambda: e.excluir()))
        eb.add_widget(card); e.add_widget(eb)
        sm.add_widget(e)
        # Config
        cfg=ConfigScreen(name='config')
        cb2=MDBoxLayout(orientation='vertical',md_bg_color=(0.04,0.04,0.04,1),spacing=dp(10),padding=dp(20))
        cb2.add_widget(MDRaisedButton(text='← Voltar',theme_bg_color='Custom',md_bg_color=(0.04,0.04,0.04,1),theme_text_color='Custom',text_color=(0.63,0.63,0.63,1),size_hint_x=None,width=dp(100),on_release=lambda: setattr(sm,'current','menu')))
        card=MDCard(orientation='vertical',md_bg_color=(0.11,0.11,0.12,1),radius=dp(12),padding=dp(20),spacing=dp(12),size_hint_y=None,height=dp(300),pos_hint={'center_x':0.5},size_hint_x=0.9)
        card.add_widget(MDLabel(text='⚙️ Configuracoes',font_style='H5',bold=True,halign='center',theme_text_color='Custom',text_color=(0.83,0.69,0.22,1)))
        vme=MDTextField(hint_text='Valor Manha',mode='rectangle',color_mode='custom',line_color_focus=(0.83,0.69,0.22,1))
        cfg.ids['vm']=vme; card.add_widget(vme)
        vne=MDTextField(hint_text='Valor Noite',mode='rectangle',color_mode='custom',line_color_focus=(0.83,0.69,0.22,1))
        cfg.ids['vn']=vne; card.add_widget(vne)
        card.add_widget(MDRaisedButton(text='Salvar',md_bg_color=(0.83,0.69,0.22,1),theme_text_color='Custom',text_color=(0,0,0,1),pos_hint={'center_x':0.5},size_hint_x=0.7,on_release=lambda: cfg.salvar()))
        cb2.add_widget(card); cfg.add_widget(cb2)
        sm.add_widget(cfg)
        return sm
    def atualizar_funcs(self):
        try: self.funcs=listar_funcs()
        except: self.funcs=[]

if __name__=='__main__':
    try:
        App().run()
    except Exception as e:
        _log_error(f'FATAL: App().run() crashed: {e}\n{traceback.format_exc()}')
