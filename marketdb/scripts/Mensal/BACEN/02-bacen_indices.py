# -*- coding: utf-8 -*-
"""
Created on Sat Apr  9 14:51:11 2016

@author: Cora.Santos
"""
import urllib, requests, zipfile, io
import pandas as pd
from bs4 import BeautifulSoup
import datetime,time
from findt import FinDt
import numpy as np

import math
import sys
from pandas.tseries.offsets import *
from pandas import ExcelWriter
import pymysql as db


###############################################################################
#----Declaração de constantes
###############################################################################

senha_bd = 'projetoinvbd'
usuario = 'Cora.Santos'
var_path= "C:\\Users\\Cora.Santos\\Desktop\\HDI-Investimentos\\Base de dados\\feriados_nacionais.csv"

#Diretório raíz
root = 'C:/Users/Cora.Santos/Desktop/HDI-Investimentos'

#Diretório de save de planilhas
save_path = root+'/codigo_fonte_final/Validacoes/'

#Conexão com Banco de Dados
connection=db.connect('localhost', user = 'root', passwd = senha_bd, db = 'projeto_inv')

###############################################################################
#----Input incremental baixado robos_diarios_bacen
###############################################################################

#Fazer a query do que foi baixado pelo robo_diario_bacen
x = 'select * from projeto_inv.bacen_series;'
bacen_series = pd.read_sql(x, con=connection)
#Retira duplicatas
bacen_series = bacen_series.sort(['codigo','data_referencia','data_bd'],ascending=[True,True,False])
bacen_series = bacen_series.drop_duplicates(subset=['codigo','data_referencia'],take_last=False)

bacen_series_mensal = bacen_series[bacen_series.frequencia.isin(['M'])].copy()
bacen_series_diario = bacen_series[bacen_series.frequencia.isin(['D'])].copy()

bacen_series_mensal = bacen_series_mensal.drop_duplicates(subset=['codigo'],take_last=True)

bacen_series = bacen_series_mensal.append(bacen_series_diario)

#Seleciona apenas IPCA, IGPM, CDI e TR
bacen_series = bacen_series[(bacen_series.codigo==256) |(bacen_series.codigo==433) | (bacen_series.codigo==189) | (bacen_series.codigo==4389) | (bacen_series.codigo==7811)]

bacen_series['indice'] = None
#IPCA - Periodocidade Mensal; Composição Mensal
bacen_series['indice'][bacen_series.codigo==433] = 'IPCA'
#IGPM - - Periodocidade Mensal; Composição Mensal
bacen_series['indice'][bacen_series.codigo==189] = 'IGP'
#CDI - - Periodocidade Diária; Composição Anual
bacen_series['indice'][bacen_series.codigo==4389] = 'DI1'
#TR - - Periodocidade Diária; Composição Mensal
bacen_series['indice'][bacen_series.codigo==7811] = 'TR'
#TJLP - - Periodocidade Diária; Composição Mensal
bacen_series['indice'][bacen_series.codigo==256] = 'TJLP'


bacen_series['data_referencia'] = bacen_series['data_referencia'].astype(str)

bacen_series['ano'] = bacen_series['data_referencia'].str[0:4].astype(int)
bacen_series['mes'] = bacen_series['data_referencia'].str[5:7].astype(int)
bacen_series['dia'] = bacen_series['data_referencia'].str[8:10].astype(int)

bacen_series['dt_ref'] = pd.to_datetime(bacen_series['data_referencia']).dt.date

del bacen_series['codigo']
del bacen_series['frequencia']
del bacen_series['nome']
del bacen_series['data_bd']
del bacen_series['id_bacen_series']
del bacen_series['data_referencia']

###############################################################################
#----ATUALIZAÇÃO ÍNDICES - CARREGAMENTO HISTÓRICO
###############################################################################

#Fazer a query do que foi baixado pelo robo_diario_anbima_projecoes
x = 'select * from projeto_inv.bc_series_hist;'
bc_series_hist = pd.read_sql(x, con=connection)

bc_series_hist = bc_series_hist.sort(['indice','dt_ref','data_bd'],ascending=[True,True,False])
bc_series_hist = bc_series_hist.drop_duplicates(subset=['indice','dt_ref'],take_last=False)

del bc_series_hist['id_bc_series_hist']
del bc_series_hist['data_bd']

horario_bd = datetime.datetime.now()

###############################################################################
#----ATUALIZAÇÃO ÍNDICES - APPEND DAS INFO NOVAS DAS SERIES BACEN
###############################################################################

bc_series_hist = bc_series_hist.append(bacen_series)

bc_series_hist = bc_series_hist.sort(['indice','dt_ref'],ascending=[True,True])
bc_series_hist = bc_series_hist.drop_duplicates(subset=['indice','dt_ref'],take_last=False)

###############################################################################
#----------CRIAÇÃO SÉRIE DIÁRIA
###############################################################################

#Seleciona o última dia do mês vigente
mesfim=datetime.date.today().month+1
fim=datetime.date(datetime.date.today().year,mesfim,1)-DateOffset(months=0, days=1)

dt_ref = pd.date_range (start='01/01/1996', end=fim, freq='D').date
ano = pd.date_range (start='01/01/1996', end=fim, freq='D').year
mes = pd.date_range (start='01/01/1996', end=fim, freq='D').month
dias = pd.date_range (start='01/01/1996', end=fim, freq='D').day
serie_dias = pd.DataFrame(columns=['dt_ref', 'ano', 'mes','dia'])
serie_dias['dt_ref']=dt_ref
serie_dias['ano']=ano
serie_dias['mes']=mes
serie_dias['dia']=dias

#identificar se é dia útil

dt_max=max(serie_dias['dt_ref'])
dt_min=min(serie_dias['dt_ref'])
per = FinDt.DatasFinanceiras(dt_min, dt_max, path_arquivo=var_path)

du=pd.DataFrame(columns=['dt_ref'])
du['dt_ref']=per.dias(3)
du['du_1']=1

serie_dias=serie_dias.merge(du, on=['dt_ref'], how='left')
serie_dias['du_1']=serie_dias['du_1'].fillna(0)
serie_dias['dc_1']=1

#calculo de dias corridos por mes
x = serie_dias[['dt_ref','ano','mes']].groupby(['ano','mes']).agg(['count'])
x = x.reset_index(level=None, drop=False, inplace=False, col_level=0, col_fill='')
x1 = pd.DataFrame(columns=['ano', 'mes', 'dc'])

x1['ano'] = x['ano']
x1['mes'] = x['mes']
x1['dc'] = x['dt_ref']

serie_dias=serie_dias.merge(x1, on = ['ano', 'mes'], how='left')

#calculo de dias uteis por mes
y = serie_dias[['du_1','ano','mes']].groupby(['ano','mes']).agg(['sum'])
y = y.reset_index(level=None, drop=False, inplace=False, col_level=0, col_fill='')
y1 = pd.DataFrame(columns=['ano', 'mes', 'du'])

y1['ano'] = y['ano']
y1['mes'] = y['mes']
y1['du'] = y['du_1']

serie_dias=serie_dias.merge(y1, on = ['ano', 'mes'], how='left')

###############################################################################
#----------CRIAÇÃO BASE DIÁRIA
###############################################################################

#----IPCA
ipca = bc_series_hist[['mes','ano','valor','indice']][bc_series_hist.indice=='IPCA'].copy()
serie_dias_ipca = serie_dias.merge(ipca,on=['mes','ano'],how='left')

#Taxas acumuladas
serie_dias_ipca['fator_dia_du'] = (1+serie_dias_ipca['du_1']*serie_dias_ipca['valor']/100)**(1/serie_dias_ipca['du'])
serie_dias_ipca['fator_dia_dc'] = (1+serie_dias_ipca['dc_1']*serie_dias_ipca['valor']/100)**(1/serie_dias_ipca['dc'])
serie_dias_ipca['fator_acum_du'] = serie_dias_ipca[['indice','fator_dia_du']].groupby(['indice']).agg(['cumprod'])
serie_dias_ipca['fator_acum_dc'] = serie_dias_ipca[['indice','fator_dia_dc']].groupby(['indice']).agg(['cumprod'])


#----IGPM
igpm = bc_series_hist[['mes','ano','valor','indice']][bc_series_hist.indice=='IGP'].copy()
serie_dias_igpm = serie_dias.merge(igpm,on=['mes','ano'],how='left')

#Taxas acumuladas
serie_dias_igpm['fator_dia_du'] = (1+serie_dias_igpm['du_1']*serie_dias_igpm['valor']/100)**(1/serie_dias_igpm['du'])
serie_dias_igpm['fator_dia_dc'] = (1+serie_dias_igpm['dc_1']*serie_dias_igpm['valor']/100)**(1/serie_dias_igpm['dc'])
serie_dias_igpm['fator_acum_du'] = serie_dias_igpm[['indice','fator_dia_du']].groupby(['indice']).agg(['cumprod'])
serie_dias_igpm['fator_acum_dc'] = serie_dias_igpm[['indice','fator_dia_dc']].groupby(['indice']).agg(['cumprod'])


#----CDI
cdi = bc_series_hist[['dia','mes','ano','valor','indice']][bc_series_hist.indice=='DI1'].copy()
serie_dias_cdi = serie_dias.merge(cdi,on=['dia','mes','ano'],how='left')
serie_dias_cdi['indice'] = serie_dias_cdi['indice'].fillna('DI1')
serie_dias_cdi['valor'] = serie_dias_cdi['valor'].fillna(0)

#Taxas acumuladas
serie_dias_cdi['fator_dia_du'] = (1+serie_dias_cdi['du_1']*serie_dias_cdi['valor']/100)**(1/252)
serie_dias_cdi['fator_dia_dc'] = None
serie_dias_cdi['fator_acum_du'] = serie_dias_cdi[['indice','fator_dia_du']].groupby(['indice']).agg(['cumprod'])
serie_dias_cdi['fator_acum_dc'] = None

#----TR
tr = bc_series_hist[['mes','ano','valor','indice']][bc_series_hist.indice=='TR'].copy()
serie_dias_tr = serie_dias.merge(tr,on=['mes','ano'],how='left')

#----TJLP
tjlp = bc_series_hist[['mes','ano','valor','indice']][bc_series_hist.indice=='TJLP'].copy()
serie_dias_tjlp = serie_dias.merge(tjlp,on=['mes','ano'],how='left')


#Taxas acumuladas
serie_dias_tr['fator_dia_du'] = (1+serie_dias_tr['du_1']*serie_dias_tr['valor']/100)**(1/serie_dias_tr['du'])
serie_dias_tr['fator_dia_dc'] = (1+serie_dias_tr['dc_1']*serie_dias_tr['valor']/100)**(1/serie_dias_tr['dc'])
serie_dias_tr['fator_acum_du'] = serie_dias_tr[['indice','fator_dia_du']].groupby(['indice']).agg(['cumprod'])
serie_dias_tr['fator_acum_dc'] = serie_dias_tr[['indice','fator_dia_dc']].groupby(['indice']).agg(['cumprod'])


serie_dias_indices = serie_dias_ipca.copy()
serie_dias_indices = serie_dias_indices.append(serie_dias_igpm)
serie_dias_indices = serie_dias_indices.append(serie_dias_cdi)
serie_dias_indices = serie_dias_indices.append(serie_dias_tr)
serie_dias_indices = serie_dias_indices.append(serie_dias_tjlp)

serie_dias_indices = serie_dias_indices[serie_dias_indices.fator_dia_du.notnull()]

serie_dias_indices = serie_dias_indices.reset_index(level=None, drop=True, inplace=False, col_level=0, col_fill='')

writer = ExcelWriter(save_path+'/serie_dias_indices.xlsx')
serie_dias_indices.to_excel(writer,'Todos')
serie_dias_ipca.to_excel(writer,'IPCA')
serie_dias_igpm.to_excel(writer,'IGPM')
serie_dias_cdi.to_excel(writer,'DI')
serie_dias_tr.to_excel(writer,'TR')
serie_dias_tjlp.to_excel(writer,'TJLP')
writer.save()

serie_dias_indices['data_bd'] = horario_bd

###############################################################################
#----------VERIFICAÇÃO PARA CRIAR A TABELA INCREMENTAL
###############################################################################

x = 'select * from projeto_inv.bc_series;'
bc_series = pd.read_sql(x, con=connection)

bc_series = bc_series[['indice','dt_ref']].copy()
bc_series['marker'] = 1

serie_dias_indices = serie_dias_indices.merge(bc_series,on=['indice','dt_ref'],how='left')
serie_dias_indices = serie_dias_indices[serie_dias_indices.marker.isnull()].copy()

del serie_dias_indices['marker']

#Conexão com Banco de Dados
connection=db.connect('localhost', user = 'root', passwd = senha_bd, db = 'projeto_inv')
#Salvar no MySQL
pd.io.sql.to_sql(serie_dias_indices, name='bc_series', con=connection, if_exists='append', flavor='mysql', index=0)