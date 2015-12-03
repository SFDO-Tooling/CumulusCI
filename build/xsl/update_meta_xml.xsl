<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:sf="http://soap.sforce.com/2006/04/metadata" xmlns="http://soap.sforce.com/2006/04/metadata"  exclude-result-prefixes="sf">

<xsl:output method="xml" standalone="yes" version="1.0" encoding="UTF-8" indent="yes" />

<xsl:param name="major" />
<xsl:param name="minor" />

<xsl:template match="node()|@*">
  <xsl:copy>
    <xsl:apply-templates select="node()|@*"/>
  </xsl:copy>
</xsl:template>

<xsl:template match="sf:packageVersions[sf:namespace = '___namespace___']/sf:majorNumber/text()">
  <xsl:value-of select="$major" /> 
</xsl:template>

<xsl:template match="sf:packageVersions[sf:namespace = '___namespace___']/sf:minorNumber/text()">
  <xsl:value-of select="$minor" /> 
</xsl:template>

</xsl:stylesheet>
