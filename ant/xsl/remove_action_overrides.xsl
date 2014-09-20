<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:sf="http://soap.sforce.com/2006/04/metadata" xmlns="http://soap.sforce.com/2006/04/metadata"  exclude-result-prefixes="sf">

<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes" />

<xsl:preserve-space elements="*"/>

<!-- Match <baz> and re-write a little -->
<xsl:template match="sf:actionOverrides">
  <actionOverrides>
    <actionName><xsl:value-of select="sf:actionName" /></actionName>
    <type>Default</type>
  </actionOverrides>
</xsl:template>

<!-- copy all nodes and attributes -->
<xsl:template match="node() | @*">
    <xsl:copy>
        <xsl:apply-templates select="node() | @*"/>
    </xsl:copy>
</xsl:template>

</xsl:stylesheet>
