#!/usr/bin/python3
# -*- coding: utf-8 -*-
# This is a part of CMSeeK, check the LICENSE file for more information
# Copyright (c) 2018 - 2019 Tuhinshubhra


def start(id, url, ua, ga, source, ga_content, headers):
    if id == "wp":
        # trust me more will be added soon
        import webscan_adapter.scanners.cmseek.VersionDetect.wp as wpverdetect
        wpver = wpverdetect.start(id, url, ua, ga, source)
        return wpver
    elif id == 'joom':
        import webscan_adapter.scanners.cmseek.VersionDetect.joom as joomverdetect
        joomver = joomverdetect.start(id, url, ua, ga, source)
        return joomver
    elif id == 'dru':
        import webscan_adapter.scanners.cmseek.VersionDetect.dru as druverdetect
        druver = druverdetect.start(id, url, ua, ga, source)
        return druver
    elif id == 'xe':
        import webscan_adapter.scanners.cmseek.VersionDetect.xe as xeverdetect
        xever = xeverdetect.start(ga_content)
        return xever
    elif id == 'wgui':
        import webscan_adapter.scanners.cmseek.VersionDetect.wgui as wguiverdetect
        wguiver = wguiverdetect.start(ga_content)
        return wguiver
    elif id == 'umi':
        import webscan_adapter.scanners.cmseek.VersionDetect.umi as umiverdetect
        umiver = umiverdetect.start(url, ua)
        return umiver
    elif id == 'tidw':
        import webscan_adapter.scanners.cmseek.VersionDetect.tidw as tidwverdetect
        tidwver = tidwverdetect.start(source)
        return tidwver
    elif id == 'sulu':
        import webscan_adapter.scanners.cmseek.VersionDetect.sulu as suluverdetect
        suluver = suluverdetect.start(url, ua)
        return suluver
    elif id == 'subcms':
        import webscan_adapter.scanners.cmseek.VersionDetect.subcms as subcmsverdetect
        subcmsver = subcmsverdetect.start(ga_content)
        return subcmsver
    elif id == 'snews':
        import webscan_adapter.scanners.cmseek.VersionDetect.snews as snewsverdetect
        snewsver = snewsverdetect.start(ga_content, source)
        return snewsver
    elif id == 'spity':
        import webscan_adapter.scanners.cmseek.VersionDetect.spity as spityverdetect
        spityver = spityverdetect.start(ga_content)
        return spityver
    elif id == 'slcms':
        import webscan_adapter.scanners.cmseek.VersionDetect.slcms as slcmsverdetect
        slcmsver = slcmsverdetect.start(source)
        return slcmsver
    elif id == 'rock':
        import webscan_adapter.scanners.cmseek.VersionDetect.rock as rockverdetect
        rockver = rockverdetect.start(ga_content)
        return rockver
    elif id == 'roadz':
        import webscan_adapter.scanners.cmseek.VersionDetect.roadz as roadzverdetect
        roadzver = roadzverdetect.start(ga_content)
        return roadzver
    elif id == 'rite':
        import webscan_adapter.scanners.cmseek.VersionDetect.rite as riteverdetect
        ritever = riteverdetect.start(ga_content)
        return ritever
    elif id == 'quick':
        import webscan_adapter.scanners.cmseek.VersionDetect.quick as quickverdetect
        quickver = quickverdetect.start(ga_content)
        return quickver
    elif id == 'pwind':
        import webscan_adapter.scanners.cmseek.VersionDetect.pwind as pwindverdetect
        pwindver = pwindverdetect.start(ga_content)
        return pwindver
    elif id == 'ophal':
        import webscan_adapter.scanners.cmseek.VersionDetect.ophal as ophalverdetect
        ophalver = ophalverdetect.start(ga_content, url, ua)
        return ophalver
    elif id == 'sfy':
        import webscan_adapter.scanners.cmseek.VersionDetect.sfy as sfyverdetect
        sfyver = sfyverdetect.start(ga_content)
        return sfyver
    elif id == 'otwsm':
        import webscan_adapter.scanners.cmseek.VersionDetect.otwsm as otwsmverdetect
        otwsmver = otwsmverdetect.start(source)
        return otwsmver
    elif id == 'ocms':
        import webscan_adapter.scanners.cmseek.VersionDetect.ocms as ocmsverdetect
        ocmsver = ocmsverdetect.start(url, ua)
        return ocmsver
    elif id == 'share':
        import webscan_adapter.scanners.cmseek.VersionDetect.share as shareverdetect
        sharever = shareverdetect.start(url, ua)
        return sharever
    elif id == 'mura':
        import webscan_adapter.scanners.cmseek.VersionDetect.mura as muraverdetect
        muraver = muraverdetect.start(ga_content)
        return muraver
    elif id == 'kbcms':
        import webscan_adapter.scanners.cmseek.VersionDetect.kbcms as kbcmsverdetect
        kbcmsver = kbcmsverdetect.start(url, ua)
        return kbcmsver
    elif id == 'koken':
        import webscan_adapter.scanners.cmseek.VersionDetect.koken as kokenverdetect
        kokenver = kokenverdetect.start(ga_content)
        return kokenver
    elif id == 'impage':
        import webscan_adapter.scanners.cmseek.VersionDetect.impage as impageverdetect
        impagever = impageverdetect.start(ga_content)
        return impagever
    elif id == 'flex':
        import webscan_adapter.scanners.cmseek.VersionDetect.flex as flexverdetect
        flexver = flexverdetect.start(source, url, ua)
        return flexver
    elif id == 'dncms':
        import webscan_adapter.scanners.cmseek.VersionDetect.dncms as dncmsverdetect
        dncmsver = dncmsverdetect.start(url, ua)
        return dncmsver
    elif id == 'cntsis':
        import webscan_adapter.scanners.cmseek.VersionDetect.cntsis as cntsisverdetect
        cntsisver = cntsisverdetect.start(ga_content)
        return cntsisver
    elif id == 'cnido':
        import webscan_adapter.scanners.cmseek.VersionDetect.cnido as cnidoverdetect
        cnidover = cnidoverdetect.start(ga_content)
        return cnidover
    elif id == 'con5':
        import webscan_adapter.scanners.cmseek.VersionDetect.con5 as con5verdetect
        con5ver = con5verdetect.start(ga_content)
        return con5ver
    elif id == 'csim':
        import webscan_adapter.scanners.cmseek.VersionDetect.csim as csimverdetect
        csimver = csimverdetect.start(ga_content)
        return csimver
    elif id == 'brcms':
        import webscan_adapter.scanners.cmseek.VersionDetect.brcms as brcmsverdetect
        brcmsver = brcmsverdetect.start(ga_content)
        return brcmsver
    elif id == 'bboard':
        import webscan_adapter.scanners.cmseek.VersionDetect.bboard as bboardverdetect
        bboardver = bboardverdetect.start(source)
        return bboardver
    elif id == 'dscrs':
        import webscan_adapter.scanners.cmseek.VersionDetect.dscrs as dscrsverdetect
        dscrsver = dscrsverdetect.start(ga_content)
        return dscrsver
    elif id == 'discuz':
        import webscan_adapter.scanners.cmseek.VersionDetect.discuz as discuzverdetect
        discuzver = discuzverdetect.start(ga_content)
        return discuzver
    elif id == 'minibb':
        import webscan_adapter.scanners.cmseek.VersionDetect.minibb as minibbverdetect
        minibbver = minibbverdetect.start(source)
        return minibbver
    elif id == 'mybb':
        import webscan_adapter.scanners.cmseek.VersionDetect.mybb as mybbverdetect
        mybbver = mybbverdetect.start(source)
        return mybbver
    elif id == 'nodebb':
        import webscan_adapter.scanners.cmseek.VersionDetect.nodebb as nodebbverdetect
        nodebbver = nodebbverdetect.start(source)
        return nodebbver
    elif id == 'punbb':
        import webscan_adapter.scanners.cmseek.VersionDetect.punbb as punbbverdetect
        punbbver = punbbverdetect.start(source)
        return punbbver
    elif id == 'smf':
        import webscan_adapter.scanners.cmseek.VersionDetect.smf as smfverdetect
        smfver = smfverdetect.start(source)
        return smfver
    elif id == 'vanilla':
        import webscan_adapter.scanners.cmseek.VersionDetect.vanilla as vanillaverdetect
        vanillaver = vanillaverdetect.start(url, ua)
        return vanillaver
    elif id == 'uknva':
        import webscan_adapter.scanners.cmseek.VersionDetect.uknva as uknvaverdetect
        uknvaver = uknvaverdetect.start(ga_content)
        return uknvaver
    elif id == 'xmb':
        import webscan_adapter.scanners.cmseek.VersionDetect.xmb as xmbverdetect
        xmbver = xmbverdetect.start(source)
        return xmbver
    elif id == 'yabb':
        import webscan_adapter.scanners.cmseek.VersionDetect.yabb as yabbverdetect
        yabbver = yabbverdetect.start(source)
        return yabbver
    elif id == 'aef':
        import webscan_adapter.scanners.cmseek.VersionDetect.aef as aefverdetect
        aefver = aefverdetect.start(source)
        return aefver
    elif id == 'bhf':
        import webscan_adapter.scanners.cmseek.VersionDetect.bhf as bhfverdetect
        bhfver = bhfverdetect.start(ga_content)
        return bhfver
    elif id == 'fudf':
        import webscan_adapter.scanners.cmseek.VersionDetect.fudf as fudfverdetect
        fudfver = fudfverdetect.start(source)
        return fudfver
    elif id == 'yaf':
        import webscan_adapter.scanners.cmseek.VersionDetect.yaf as yafverdetect
        yafver = yafverdetect.start(source)
        return yafver
    elif id == 'ubbt':
        import webscan_adapter.scanners.cmseek.VersionDetect.ubbt as ubbtverdetect
        ubbtver = ubbtverdetect.start(source, ga_content)
        return ubbtver
    elif id == 'myupb':
        import webscan_adapter.scanners.cmseek.VersionDetect.myupb as myupbverdetect
        myupbver = myupbverdetect.start(source)
        return myupbver
    elif id == 'mvnf':
        import webscan_adapter.scanners.cmseek.VersionDetect.mvnf as mvnfverdetect
        mvnfver = mvnfverdetect.start(source)
        return mvnfver
    elif id == 'mcb':
        import webscan_adapter.scanners.cmseek.VersionDetect.mcb as mcbverdetect
        mcbver = mcbverdetect.start(source)
        return mcbver
    elif id == 'aspf':
        import webscan_adapter.scanners.cmseek.VersionDetect.aspf as aspfverdetect
        aspfver = aspfverdetect.start(source)
        return aspfver
    elif id == 'jf':
        import webscan_adapter.scanners.cmseek.VersionDetect.jf as jfverdetect
        jfver = jfverdetect.start(source)
        return jfver
    elif id == 'mg':
        import webscan_adapter.scanners.cmseek.VersionDetect.mg as mgverdetect
        mgver = mgverdetect.start(url, ua)
        return mgver
    elif id == 'coms':
        import webscan_adapter.scanners.cmseek.VersionDetect.coms as comsverdetect
        comsver = comsverdetect.start(url, ua)
        return comsver
    elif id == 'abda':
        import webscan_adapter.scanners.cmseek.VersionDetect.abda as abdaverdetect
        abdaver = abdaverdetect.start(source)
        return abdaver
    elif id == 'dweb':
        import webscan_adapter.scanners.cmseek.VersionDetect.dweb as dwebverdetect
        dwebver = dwebverdetect.start(ga_content)
        return dwebver
    elif id == 'qcart':
        import webscan_adapter.scanners.cmseek.VersionDetect.qcart as qcartverdetect
        qcartver = qcartverdetect.start(ga_content)
        return qcartver
    elif id == 'rbsc':
        import webscan_adapter.scanners.cmseek.VersionDetect.rbsc as rbscverdetect
        rbscver = rbscverdetect.start(ga_content)
        return rbscver
    elif id == 'oracle_atg':
        import webscan_adapter.scanners.cmseek.VersionDetect.atg as atgverdetect
        atgver = atgverdetect.start(headers)
        return atgver
    elif id == 'umbraco':
        import webscan_adapter.scanners.cmseek.VersionDetect.umbraco as umbracoverdetect
        umbracover = umbracoverdetect.start(headers, url, ua)
        return umbracover
    elif id == 'shopfa':
        import webscan_adapter.scanners.cmseek.VersionDetect.shopfa as shopfaverdetect
        shopfaver = shopfaverdetect.start(ga_content, headers)
        return shopfaver
